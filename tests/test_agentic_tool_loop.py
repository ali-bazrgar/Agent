from __future__ import annotations

from typing import Any

from superagent.llm.agentic_provider import AgenticLLMProvider
from superagent.models.domain import MemoryRecord
from superagent.providers.contracts import LLMProvider, LLMRequest, LLMResponse, LLMToolCall, ProviderCapabilities, ProviderHealth, ProviderHealthStatus
from superagent.repositories.ports import MemoryRepository
from superagent.tools.memory import MemoryWriteTool
from superagent.tools.models import ToolCall, ToolDefinition, ToolExecutionContext, ToolExecutionStatus, ToolResult
from superagent.tools.ports import ToolExecutorPort, ToolProvider, ToolRegistryPort


class EchoTool(ToolProvider):
    @property
    def definition(self) -> ToolDefinition:
        return ToolDefinition(name="test.echo", description="Echo text", input_schema={"type": "object", "properties": {"text": {"type": "string"}}, "required": ["text"]})

    def execute(self, call: ToolCall, context: ToolExecutionContext | None = None) -> ToolResult:
        return ToolResult(tool_call_id=call.tool_call_id, tool_name=call.tool_name, status=ToolExecutionStatus.SUCCESS, output={"echo": call.arguments["text"]})


class Registry(ToolRegistryPort):
    def __init__(self, tool: ToolProvider | None = None) -> None:
        self.tool = tool or EchoTool()

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


class MemoryRepositoryFake(MemoryRepository):
    def __init__(self) -> None:
        self.items: dict[str, MemoryRecord] = {}

    def create_memory(self, memory: MemoryRecord) -> MemoryRecord:
        self.items[memory.memory_id] = memory
        return memory

    def get_memory(self, memory_id: str) -> MemoryRecord | None:
        return self.items.get(memory_id)

    def list_memories(self) -> list[MemoryRecord]:
        return list(self.items.values())

    def update_memory(self, memory: MemoryRecord) -> MemoryRecord:
        self.items[memory.memory_id] = memory
        return memory

    def update_status(self, memory_id: str, status: str) -> None:
        memory = self.items[memory_id]
        self.items[memory_id] = memory.model_copy(update={"status": status})


class MemoryLLM(LLMProvider):
    def __init__(self) -> None:
        self.requests: list[LLMRequest] = []
        self.round = 0

    def complete(self, request: LLMRequest) -> LLMResponse:
        self.requests.append(request)
        self.round += 1
        if self.round == 1:
            return LLMResponse(
                tool_calls=[
                    LLMToolCall(
                        id="memory-call-1",
                        name="memory.write",
                        arguments={"content": "من پایتون را دوست دارم.", "kind": "user"},
                    )
                ],
                finish_reason="tool_calls",
            )
        return LLMResponse(text="ذخیره شد.", finish_reason="stop")

    def check_health(self) -> ProviderHealth:
        return ProviderHealth(name="fake-memory", status=ProviderHealthStatus.HEALTHY)

    def capabilities(self) -> ProviderCapabilities:
        return ProviderCapabilities(chat=True, tool_calling=True)


def test_memory_is_selected_by_model_without_language_specific_trigger_rules() -> None:
    repository = MemoryRepositoryFake()
    memory_tool = MemoryWriteTool(repository)
    registry = Registry(memory_tool)
    executor = Executor(registry)
    inner = MemoryLLM()
    provider = AgenticLLMProvider(inner, registry, executor)

    response = provider.complete(LLMRequest(prompt="این اطلاعات را برای آینده در نظر بگیر: من پایتون را دوست دارم."))

    assert response.text == "ذخیره شد."
    assert len(repository.items) == 1
    saved = next(iter(repository.items.values()))
    assert saved.content == "من پایتون را دوست دارم."
    assert saved.kind.value == "user"
    assert executor.calls[0].tool_name == "memory.write"
    assert "ذخیره" not in saved.content
    assert inner.requests[0].tools[0]["function"]["name"] == "memory.write"


def test_tool_call_budget_is_shared_across_rounds() -> None:
    registry = Registry()
    executor = Executor(registry)

    class AlwaysToolLLM(FakeLLM):
        def complete(self, request: LLMRequest) -> LLMResponse:
            self.requests.append(request)
            self.round += 1
            return LLMResponse(tool_calls=[LLMToolCall(id=f"call-{self.round}", name="test.echo", arguments={"text": "x"})], finish_reason="tool_calls")

    inner = AlwaysToolLLM()
    provider = AgenticLLMProvider(inner, registry, executor, max_rounds=4, max_tool_calls=1)
    response = provider.complete(LLMRequest(prompt="use a tool"))

    assert len(executor.calls) == 1
    assert response.finish_reason == "tool_loop_limit"
    assert len(inner.requests) == 2
    assert any('Maximum tool calls (1) exceeded.' in request.messages[-1]["content"] for request in inner.requests[1:])
