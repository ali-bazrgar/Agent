from __future__ import annotations

from typing import Any

from superagent.llm.agentic_provider import AgenticLLMProvider
from superagent.providers.contracts import LLMProvider, LLMRequest, LLMResponse, LLMToolCall, ProviderCapabilities, ProviderHealth, ProviderHealthStatus
from superagent.tools.models import ToolCall, ToolDefinition, ToolExecutionContext, ToolExecutionStatus, ToolResult
from superagent.tools.ports import ToolExecutorPort, ToolProvider, ToolRegistryPort


class EchoTool(ToolProvider):
    @property
    def definition(self) -> ToolDefinition:
        return ToolDefinition(name="test.echo", description="Echo text", input_schema={"type": "object", "properties": {"text": {"type": "string"}}, "required": ["text"]})

    def execute(self, call: ToolCall, context: ToolExecutionContext | None = None) -> ToolResult:
        return ToolResult(tool_call_id=call.tool_call_id, tool_name=call.tool_name, status=ToolExecutionStatus.SUCCESS, output={"echo": call.arguments["text"]})


class Registry(ToolRegistryPort):
    def __init__(self) -> None:
        self.tool = EchoTool()

    def register(self, tool: ToolProvider) -> None:
        self.tool = tool

    def unregister(self, tool_name: str) -> None:
        pass

    def get(self, tool_name: str) -> ToolProvider | None:
        return self.tool if tool_name == self.tool.definition.name else None

    def list_tools(self) -> list[ToolDefinition]:
        return [self.tool.definition]

    def has(self, tool_name: str) -> bool:
        return self.get(tool_name) is not None


class Executor(ToolExecutorPort):
    def __init__(self, registry: Registry) -> None:
        self.registry = registry
        self.calls: list[ToolCall] = []

    def execute_tool(self, call: ToolCall, context: ToolExecutionContext | None = None) -> ToolResult:
        self.calls.append(call)
        tool = self.registry.get(call.tool_name)
        assert tool is not None
        return tool.execute(call, context)

    def execute_tools(self, calls: list[ToolCall], context: ToolExecutionContext | None = None) -> list[ToolResult]:
        return [self.execute_tool(call, context) for call in calls]


class FakeLLM(LLMProvider):
    def __init__(self) -> None:
        self.requests: list[LLMRequest] = []
        self.round = 0

    def complete(self, request: LLMRequest) -> LLMResponse:
        self.requests.append(request)
        self.round += 1
        if self.round == 1:
            return LLMResponse(tool_calls=[LLMToolCall(id="call-1", name="test.echo", arguments={"text": "hello"})], finish_reason="tool_calls")
        return LLMResponse(text="Tool result received.", finish_reason="stop")

    def check_health(self) -> ProviderHealth:
        return ProviderHealth(name="fake", status=ProviderHealthStatus.HEALTHY)

    def capabilities(self) -> ProviderCapabilities:
        return ProviderCapabilities(chat=True, tool_calling=True)


def test_model_selected_tool_is_executed_and_observed() -> None:
    registry = Registry()
    executor = Executor(registry)
    inner = FakeLLM()
    provider = AgenticLLMProvider(inner, registry, executor)

    response = provider.complete(LLMRequest(prompt="Please use the appropriate capability."))

    assert response.text == "Tool result received."
    assert len(executor.calls) == 1
    assert executor.calls[0].tool_name == "test.echo"
    assert executor.calls[0].arguments == {"text": "hello"}
    assert len(inner.requests) == 2
    assert inner.requests[0].tools
    assert inner.requests[0].tool_choice == "auto"
    assert inner.requests[1].messages[-1]["role"] == "tool"
    assert "hello" in inner.requests[1].messages[-1]["content"]
