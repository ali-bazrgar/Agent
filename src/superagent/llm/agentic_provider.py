from __future__ import annotations

import json
from typing import Any

from superagent.config.settings import Settings, get_settings
from superagent.llm.capabilities import ModelCapabilityRegistry
from superagent.llm.capability_policy import CapabilityPolicy
from superagent.providers.contracts import LLMProvider, LLMRequest, LLMResponse, ProviderCapabilities, ProviderHealth
from superagent.tools.models import ToolCall, ToolExecutionContext
from superagent.tools.ports import ToolExecutorPort, ToolRegistryPort


_TRUSTED_PRINCIPAL_METADATA_KEY = "_trusted_principal"


class AgenticLLMProvider(LLMProvider):
    """Adds a bounded model-selected tool loop around an LLM provider."""

    def __init__(self, inner: LLMProvider, registry: ToolRegistryPort, executor: ToolExecutorPort, max_rounds: int = 4, max_tool_calls: int = 8, settings: Settings | None = None) -> None:
        self.inner = inner
        self.registry = registry
        self.executor = executor
        self.max_rounds = max(1, max_rounds)
        self.max_tool_calls = max(1, max_tool_calls)
        self.settings = settings or get_settings()
        self._capability_registry = ModelCapabilityRegistry()

    def _effective_capabilities(self) -> ProviderCapabilities:
        provider = self.inner.capabilities()
        model_id = self.settings.llm_model_id
        if not model_id:
            if self.settings.require_verified_capabilities:
                return provider.model_copy(update={"tool_calling": False, "structured_output": False})
            return provider
        policy = CapabilityPolicy(self._capability_registry, require_verified=self.settings.require_verified_capabilities, tools_enabled=self.settings.tools_enabled, structured_output_enabled=self.settings.structured_output_enabled)
        overrides = self.settings.model_capability_overrides.get(model_id, {})
        policy.register_model(model_id, provider, overrides=overrides)
        effective = policy.effective(model_id, provider)
        return ProviderCapabilities(**effective.model_dump())

    @staticmethod
    def _tool_context(request: LLMRequest, max_tool_calls: int) -> ToolExecutionContext:
        principal = request.metadata.get(_TRUSTED_PRINCIPAL_METADATA_KEY)
        context = ToolExecutionContext(
            execution_id=request.metadata.get("_execution_id"),
            conversation_id=request.metadata.get("_conversation_id"),
            project_id=request.metadata.get("_project_id"),
            metadata={"max_tool_calls": max_tool_calls, "tool_call_count": 0, "agentic_tool_call_count": 0},
        )
        if principal is not None:
            principal_id = getattr(principal, "principal_id", None)
            principal_type = getattr(principal, "principal_type", None)
            if isinstance(principal_id, str) and principal_id.strip():
                context.principal_id = principal_id
                context.metadata["principal_type"] = principal_type or "user"
        return context

    @staticmethod
    def _provider_request(request: LLMRequest, messages: list[dict[str, Any]], tools: list[dict[str, Any]]) -> LLMRequest:
        metadata = dict(request.metadata)
        metadata.pop(_TRUSTED_PRINCIPAL_METADATA_KEY, None)
        return request.model_copy(update={"messages": messages, "tools": tools, "tool_choice": request.tool_choice, "metadata": metadata})

    def complete(self, request: LLMRequest) -> LLMResponse:
        effective = self._effective_capabilities()
        if not effective.tool_calling or not self.settings.llm_driven_tools:
            sanitized = request.model_copy(update={"metadata": {k: v for k, v in request.metadata.items() if k != _TRUSTED_PRINCIPAL_METADATA_KEY}})
            return self.inner.complete(sanitized)
        definitions = request.tools or [self._openai_tool_schema(item.model_dump(mode="json")) for item in self.registry.list_tools()]
        current_messages = list(request.messages)
        total_usage = 0
        tool_calls_executed: list[dict[str, Any]] = []
        context = self._tool_context(request, self.max_tool_calls)
        response: LLMResponse | None = None
        for round_index in range(self.max_rounds):
            current = self._provider_request(request, current_messages, definitions)
            response = self.inner.complete(current)
            if response.token_usage:
                total_usage += response.token_usage
            if not response.tool_calls:
                response.metadata.update({"tool_calls_executed": tool_calls_executed, "tools_used": bool(tool_calls_executed), "tool_rounds": round_index + 1})
                if total_usage and not response.token_usage:
                    response.token_usage = total_usage
                return response
            current_messages.append({"role": "assistant", "content": response.text or None, "tool_calls": [{"id": call.id, "type": "function", "function": {"name": call.name, "arguments": self._json(call.arguments)}} for call in response.tool_calls]})
            for call in response.tool_calls:
                agentic_count = int(context.metadata.get("agentic_tool_call_count", 0))
                if agentic_count >= self.max_tool_calls:
                    current_messages.append(self._budget_error_message(call.id))
                    return self._limit_response(response, total_usage, tool_calls_executed, round_index + 1)
                context.metadata["agentic_tool_call_count"] = agentic_count + 1
                result = self.executor.execute_tool(ToolCall(tool_call_id=call.id, tool_name=call.name, arguments=call.arguments), context)
                tool_calls_executed.append({"id": call.id, "name": call.name, "status": result.status.value})
                current_messages.append({"role": "tool", "tool_call_id": result.tool_call_id, "content": self._json({"status": result.status.value, "output": result.output, "error": result.error})})
                if int(context.metadata.get("agentic_tool_call_count", 0)) >= self.max_tool_calls:
                    current_messages.append(self._budget_error_message(call.id))
                    if round_index + 1 < self.max_rounds:
                        break
                    return self._limit_response(response, total_usage, tool_calls_executed, round_index + 1)
            else:
                continue
            final_request = self._provider_request(request, current_messages, definitions)
            final_response = self.inner.complete(final_request)
            if final_response.token_usage:
                total_usage += final_response.token_usage
            return self._limit_response(final_response, total_usage, tool_calls_executed, round_index + 2)
        assert response is not None
        return LLMResponse(text="The tool execution loop reached its maximum number of rounds before a final answer was produced.", model_id=response.model_id, token_usage=total_usage or response.token_usage, provider_name=response.provider_name, finish_reason="tool_loop_limit", metadata={"tool_calls_executed": tool_calls_executed, "tools_used": bool(tool_calls_executed), "tool_rounds": self.max_rounds})

    def _budget_error_message(self, tool_call_id: str) -> dict[str, str]:
        return {"role": "tool", "tool_call_id": tool_call_id, "content": f"Maximum tool calls ({self.max_tool_calls}) exceeded."}

    @staticmethod
    def _limit_response(response: LLMResponse, total_usage: int, tool_calls_executed: list[dict[str, Any]], rounds: int) -> LLMResponse:
        return LLMResponse(text="The tool execution limit was reached before a final answer was produced.", model_id=response.model_id, token_usage=total_usage or response.token_usage, provider_name=response.provider_name, finish_reason="tool_loop_limit", metadata={"tool_calls_executed": tool_calls_executed, "tools_used": True, "tool_rounds": rounds})

    def check_health(self) -> ProviderHealth:
        return self.inner.check_health()

    def capabilities(self) -> ProviderCapabilities:
        return self._effective_capabilities()

    @staticmethod
    def _openai_tool_schema(definition: dict[str, Any]) -> dict[str, Any]:
        parameters = definition.get("input_schema") or {"type": "object", "properties": {}}
        return {"type": "function", "function": {"name": definition["name"], "description": definition.get("description", ""), "parameters": parameters}}

    @staticmethod
    def _json(value: Any) -> str:
        return json.dumps(value, ensure_ascii=False, default=str)
