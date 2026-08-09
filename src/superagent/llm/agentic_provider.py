from __future__ import annotations

from typing import Any

from superagent.providers.contracts import LLMProvider, LLMRequest, LLMResponse, ProviderCapabilities, ProviderHealth
from superagent.tools.models import ToolCall, ToolExecutionContext
from superagent.tools.ports import ToolExecutorPort, ToolRegistryPort


class AgenticLLMProvider(LLMProvider):
    """Adds a bounded model-selected tool loop around any LLM provider.

    The model chooses tools from schemas supplied by the registry. This layer
    executes only the calls returned by the model and feeds observations back
    into the model; it contains no language-specific intent keywords.
    """

    def __init__(self, inner: LLMProvider, registry: ToolRegistryPort, executor: ToolExecutorPort, max_rounds: int = 4) -> None:
        self.inner = inner
        self.registry = registry
        self.executor = executor
        self.max_rounds = max(1, max_rounds)

    def complete(self, request: LLMRequest) -> LLMResponse:
        definitions = request.tools or [self._openai_tool_schema(item.model_dump(mode="json")) for item in self.registry.list_tools()]
        current_messages = list(request.messages)
        last = request
        total_usage = 0
        for _ in range(self.max_rounds):
            last = self.inner.complete(last.model_copy(update={"messages": current_messages, "tools": definitions, "tool_choice": "auto"}))
            if last.token_usage:
                total_usage += last.token_usage
            if not last.tool_calls:
                if total_usage and not last.token_usage:
                    last.token_usage = total_usage
                return last
            assistant_message: dict[str, Any] = {
                "role": "assistant",
                "content": last.text or None,
                "tool_calls": [
                    {"id": call.id, "type": "function", "function": {"name": call.name, "arguments": self._json(call.arguments)}}
                    for call in last.tool_calls
                ],
            }
            current_messages.append(assistant_message)
            results = []
            for call in last.tool_calls:
                result = self.executor.execute_tool(
                    ToolCall(tool_call_id=call.id, tool_name=call.name, arguments=call.arguments),
                    ToolExecutionContext(metadata={"max_tool_calls": 8}),
                )
                results.append(result)
                current_messages.append({
                    "role": "tool",
                    "tool_call_id": result.tool_call_id,
                    "content": self._json({
                        "status": result.status.value,
                        "output": result.output,
                        "error": result.error,
                    }),
                })
            if results:
                continue
        return LLMResponse(
            text="The tool execution limit was reached before a final answer was produced.",
            model_id=last.model_id,
            token_usage=total_usage or last.token_usage,
            provider_name=last.provider_name,
            finish_reason="tool_loop_limit",
        )

    def check_health(self) -> ProviderHealth:
        return self.inner.check_health()

    def capabilities(self) -> ProviderCapabilities:
        capabilities = self.inner.capabilities()
        capabilities.tool_calling = True
        return capabilities

    def _openai_tool_schema(self, definition: dict[str, Any]) -> dict[str, Any]:
        return {"type": "function", "function": {"name": definition["name"], "description": definition.get("description", ""), "parameters": definition.get("input_schema") or {"type": "object", "properties": {}}}}

    @staticmethod
    def _json(value: Any) -> str:
        import json
        return json.dumps(value, ensure_ascii=False, default=str)
