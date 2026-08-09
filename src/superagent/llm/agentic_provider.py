from __future__ import annotations

import json
from typing import Any

from superagent.providers.contracts import LLMProvider, LLMRequest, LLMResponse, ProviderCapabilities, ProviderHealth
from superagent.tools.models import ToolCall, ToolExecutionContext
from superagent.tools.ports import ToolExecutorPort, ToolRegistryPort


class AgenticLLMProvider(LLMProvider):
    """Adds a bounded model-selected tool loop around an LLM provider."""

    def __init__(self, inner: LLMProvider, registry: ToolRegistryPort, executor: ToolExecutorPort, max_rounds: int = 4, max_tool_calls: int = 8) -> None:
        self.inner = inner
        self.registry = registry
        self.executor = executor
        self.max_rounds = max(1, max_rounds)
        self.max_tool_calls = max(1, max_tool_calls)

    def complete(self, request: LLMRequest) -> LLMResponse:
        if not self.inner.capabilities().tool_calling:
            return self.inner.complete(request)

        definitions = request.tools or [self._openai_tool_schema(item.model_dump(mode="json")) for item in self.registry.list_tools()]
        current_messages = list(request.messages)
        total_usage = 0
        tool_calls_executed: list[dict[str, Any]] = []
        context = ToolExecutionContext(metadata={"max_tool_calls": self.max_tool_calls, "tool_call_count": 0})
        response: LLMResponse | None = None

        for round_index in range(self.max_rounds):
            current = request.model_copy(update={"messages": current_messages, "tools": definitions, "tool_choice": request.tool_choice})
            response = self.inner.complete(current)
            if response.token_usage:
                total_usage += response.token_usage

            if not response.tool_calls:
                response.metadata.update({"tool_calls_executed": tool_calls_executed, "tools_used": bool(tool_calls_executed), "tool_rounds": round_index + 1})
                if total_usage and not response.token_usage:
                    response.token_usage = total_usage
                return response

            current_messages.append({
                "role": "assistant",
                "content": response.text or None,
                "tool_calls": [{"id": call.id, "type": "function", "function": {"name": call.name, "arguments": self._json(call.arguments)}} for call in response.tool_calls],
            })

            for call in response.tool_calls:
                result = self.executor.execute_tool(ToolCall(tool_call_id=call.id, tool_name=call.name, arguments=call.arguments), context)
                tool_calls_executed.append({"id": call.id, "name": call.name, "status": result.status.value})
                current_messages.append({"role": "tool", "tool_call_id": result.tool_call_id, "content": self._json({"status": result.status.value, "output": result.output, "error": result.error})})

                if int(context.metadata.get("tool_call_count", 0)) >= self.max_tool_calls:
                    return LLMResponse(
                        text="The tool execution limit was reached before a final answer was produced.",
                        model_id=response.model_id,
                        token_usage=total_usage or response.token_usage,
                        provider_name=response.provider_name,
                        finish_reason="tool_loop_limit",
                        metadata={"tool_calls_executed": tool_calls_executed, "tools_used": True, "tool_rounds": round_index + 1},
                    )

        assert response is not None
        return LLMResponse(
            text="The tool execution loop reached its maximum number of rounds before a final answer was produced.",
            model_id=response.model_id,
            token_usage=total_usage or response.token_usage,
            provider_name=response.provider_name,
            finish_reason="tool_loop_limit",
            metadata={"tool_calls_executed": tool_calls_executed, "tools_used": bool(tool_calls_executed), "tool_rounds": self.max_rounds},
        )

    def check_health(self) -> ProviderHealth:
        return self.inner.check_health()

    def capabilities(self) -> ProviderCapabilities:
        return self.inner.capabilities().model_copy(deep=True)

    @staticmethod
    def _openai_tool_schema(definition: dict[str, Any]) -> dict[str, Any]:
        parameters = definition.get("input_schema") or {"type": "object", "properties": {}}
        return {"type": "function", "function": {"name": definition["name"], "description": definition.get("description", ""), "parameters": parameters}}

    @staticmethod
    def _json(value: Any) -> str:
        return json.dumps(value, ensure_ascii=False, default=str)
