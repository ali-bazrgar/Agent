from superagent.llm.agentic_provider import AgenticLLMProvider
from superagent.providers.contracts import LLMProvider, LLMRequest, LLMResponse, LLMToolCall, ProviderCapabilities, ProviderHealth, ProviderHealthStatus
from superagent.tools.models import ToolCall, ToolDefinition, ToolExecutionContext, ToolExecutionStatus, ToolResult
from superagent.tools.ports import ToolExecutorPort, ToolProvider, ToolRegistryPort


class Echo(ToolProvider):
    @property
    def definition(self) -> ToolDefinition:
        return ToolDefinition(name="test.echo", description="Echo", input_schema={"type": "object", "properties": {"text": {"type": "string"}}})

    def execute(self, call: ToolCall, context: ToolExecutionContext | None = None) -> ToolResult:
        return ToolResult(tool_call_id=call.tool_call_id, tool_name=call.tool_name, status=ToolExecutionStatus.SUCCESS, output=call.arguments)


class Registry(ToolRegistryPort):
    def __init__(self) -> None:
        self.tool = Echo()

    def register(self, tool: ToolProvider) -> None:
        self.tool = tool

    def unregister(self, tool_name: str) -> None:
        pass

    def get(self, tool_name: str) -> ToolProvider | None:
        return self.tool if tool_name == self.tool.definition.name else None

    def list_tools(self) -> list[ToolDefinition]:
        return [self.tool.definition]

    def has(self, tool_name: str) -> bool:
        return tool_name == self.tool.definition.name


class Executor(ToolExecutorPort):
    def __init__(self, registry: Registry) -> None:
        self.registry = registry
        self.calls = 0

    def execute_tool(self, call: ToolCall, context: ToolExecutionContext | None = None) -> ToolResult:
        self.calls += 1
        return self.registry.get(call.tool_name).execute(call, context)  # type: ignore[union-attr]

    def execute_tools(self, calls: list[ToolCall], context: ToolExecutionContext | None = None) -> list[ToolResult]:
        return [self.execute_tool(call, context) for call in calls]


class AlwaysTool(LLMProvider):
    def __init__(self) -> None:
        self.round = 0

    def complete(self, request: LLMRequest) -> LLMResponse:
        self.round += 1
        return LLMResponse(tool_calls=[LLMToolCall(id=f"call-{self.round}", name="test.echo", arguments={"text": "x"})], finish_reason="tool_calls")

    def check_health(self) -> ProviderHealth:
        return ProviderHealth(name="fake", status=ProviderHealthStatus.HEALTHY)

    def capabilities(self) -> ProviderCapabilities:
        return ProviderCapabilities(chat=True, tool_calling=True)


def test_execution_reserver_is_called_before_each_agentic_tool() -> None:
    registry = Registry()
    executor = Executor(registry)
    calls: list[int] = []

    def reserve() -> None:
        calls.append(1)
        if len(calls) > 1:
            raise RuntimeError("global tool budget exhausted")

    provider = AgenticLLMProvider(AlwaysTool(), registry, executor, max_rounds=4, max_tool_calls=4)
    response = provider.complete(LLMRequest(prompt="use tools", metadata={"_tool_call_reserver": reserve}))

    assert len(calls) == 2
    assert executor.calls == 1
    assert response.finish_reason == "tool_loop_limit" or response.text
