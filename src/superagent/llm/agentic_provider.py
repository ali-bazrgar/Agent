from __future__ import annotations

import json
from typing import Any

from superagent.config.settings import Settings, get_settings
from superagent.llm.capabilities import ModelCapabilityRegistry
from superagent.llm.capability_policy import CapabilityPolicy
from superagent.llm.runtime import ModelRuntimeConfig
from superagent.providers.contracts import LLMProvider, LLMRequest, LLMResponse, ProviderCapabilities, ProviderHealth
from superagent.tools.models import ToolCall, ToolExecutionContext
from superagent.tools.ports import ToolExecutorPort, ToolRegistryPort


class AgenticLLMProvider(LLMProvider):
    """Adds a bounded model-selected tool loop around an LLM provider."""

    def __init__(self, inner: LLMProvider, registry: ToolRegistryPort, executor: ToolExecutorPort, max_rounds: int = 4, max_tool_calls: int = 8, settings: Settings | None = None, runtime_config: ModelRuntimeConfig | None = None) -> None:
        self.inner = inner
        self.registry = registry
        self.executor = executor
        self.max_rounds = max(1, max_rounds)
        self.max_tool_calls = max(1, max_tool_calls)
        self.settings = settings or get_settings()
        self.runtime_config = runtime_config
        self._capability_registry = ModelCapabilityRegistry()

    def _effective_capabilities(self) -> ProviderCapabilities:
        provider = self.inner.capabilities()
        model_id = self.runtime_config.model_id if self.runtime_config is not None else self.settings.llm_model_id
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
    def _record_usage(metadata: dict[str, Any], response: LLMResponse) -> None:
        recorder = metadata.get("_model_usage_recorder")
        if not callable(recorder):
            reserver = metadata.get("_tool_call_reserver")
            owner = getattr(reserver, "__self__", None) if callable(reserver) else None
            recorder = getattr(owner, "record_model_usage", None)
        if callable(recorder):
            recorder(response.token_usage)

    def complete(self, request: LLMRequest) -> LLMResponse:
        effective = self._effective_capabilities()
        metadata = request.metadata if isinstance(request.metadata, dict) else {}
        if metadata.get("disable_tools") is True or not effective.tool_calling or not self.settings.llm_driven_tools:
            response = self.inner.complete(request)
            self._record_usage(metadata, response)
            return response
        definitions = request.tools or [self._openai_tool_schema(item.model_dump(mode="json")) for item in self.registry.list_tools()]
        current_messages = list(request.messages)
        total_usage = 0
        tool_calls_executed: list[dict[str, Any]] = []
        tool_results: list[dict[str, Any]] = []
        context = ToolExecutionContext(metadata={"max_tool_calls": self.max_tool_calls, "tool_call_count": 0, "agentic_tool_call_count": 0})
        reserver = metadata.get("_tool_call_reserver")
        if reserver is not None and not callable(reserver):
            reserver = None
        response: LLMResponse | None = None
        for round_index in range(self.max_rounds):
            current = request.model_copy(update={"messages": current_messages, "tools": definitions, "tool_choice": request.tool_choice})
            response = self.inner.complete(current)
            self._record_usage(metadata, response)
            if response.token_usage:
                total_usage += response.token_usage
            if not response.tool_calls:
                response.metadata.update({"tool_calls_executed": tool_calls_executed, "tool_results": tool_results, "tools_used": bool(tool_calls_executed), "tool_rounds": round_index + 1})
                if total_usage and not response.token_usage:
                    response.token_usage = total_usage
                return response
            current_messages.append({"role": "assistant", "content": response.text or None, "tool_calls": [{"id": call.id, "type": "function", "function": {"name": call.name, "arguments": self._json(call.arguments)}} for call in response.tool_calls]})
            for call in response.tool_calls:
                agentic_count = int(context.metadata.get("agentic_tool_call_count", 0))
                if agentic_count >= self.max_tool_calls:
                    current_messages.append(self._budget_error_message(call.id))
                    return self._limit_response(response, total_usage, tool_calls_executed, tool_results, round_index + 1)
                if reserver is not None:
                    reserver()
                context.metadata["agentic_tool_call_count"] = agentic_count + 1
                result = self.executor.execute_tool(ToolCall(tool_call_id=call.id, tool_name=call.name, arguments=call.arguments), context)
                tool_calls_executed.append({"id": call.id, "name": call.name, "status": result.status.value})
                tool_results.append({"id": result.tool_call_id, "name": result.tool_name, "status": result.status.value, "output": result.output, "error": result.error, "metadata": result.metadata})
                current_messages.append({"role": "tool", "tool_call_id": result.tool_call_id, "content": self._json({"status": result.status.value, "output": result.output, "error": result.error})})
                if int(context.metadata.get("agentic_tool_call_count", 0)) >= self.max_tool_calls:
                    current_messages.append(self._budget_error_message(call.id))
                    if round_index + 1 < self.max_rounds:
                        break
                    return self._limit_response(response, total_usage, tool_calls_executed, tool_results, round_index + 1)
            else:
                continue
            final_request = request.model_copy(update={"messages": current_messages, "tools": definitions, "tool_choice": request.tool_choice})
            final_response = self.inner.complete(final_request)
            self._record_usage(metadata, final_response)
            if final_response.token_usage:
                total_usage += final_response.token_usage
            return self._limit_response(final_response, total_usage, tool_calls_executed, tool_results, round_index + 2)
        assert response is not None
        return LLMResponse(text="The tool execution loop reached its maximum number of rounds before a final answer was produced.", model_id=response.model_id, token_usage=total_usage or response.token_usage, provider_name=response.provider_name, finish_reason="tool_loop_limit", metadata={"tool_calls_executed": tool_calls_executed, "tool_results": tool_results, "tools_used": bool(tool_calls_executed), "tool_rounds": self.max_rounds})

    def _budget_error_message(self, tool_call_id: str) -> dict[str, str]:
        return {"role": "tool", "tool_call_id": tool_call_id, "content": f"Maximum tool calls ({self.max_tool_calls}) exceeded."}

    @staticmethod
    def _limit_response(response: LLMResponse, total_usage: int, tool_calls_executed: list[dict[str, Any]], tool_results: list[dict[str, Any]], rounds: int) -> LLMResponse:
        return LLMResponse(text="The tool execution limit was reached before a final answer could be produced.", model_id=response.model_id, token_usage=total_usage or response.token_usage, provider_name=response.provider_name, finish_reason="tool_loop_limit", metadata={"tool_calls_executed": tool_calls_executed, "tool_results": tool_results, "tools_used": True, "tool_rounds": rounds})

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
