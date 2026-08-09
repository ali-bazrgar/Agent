from __future__ import annotations

from typing import Sequence

from superagent.context.request import Principal
from superagent.llm.agentic_provider import AgenticLLMProvider
from superagent.models.domain import MemoryRecord
from superagent.providers.contracts import (
    LLMProvider,
    LLMRequest,
    LLMResponse,
    LLMToolCall,
    ProviderCapabilities,
    ProviderHealth,
    ProviderHealthStatus,
)
from superagent.repositories.ports import MemoryRepository
from superagent.tools.executor import ToolExecutor
from superagent.tools.memory import MemorySearchTool, MemoryWriteTool
from superagent.tools.models import ToolCall, ToolExecutionContext, ToolExecutionStatus, ToolResult
from superagent.tools.registry import ToolRegistry


class InMemoryMemoryRepository(MemoryRepository):
    def __init__(self) -> None:
        self.items: dict[str, MemoryRecord] = {}

    def create_memory(self, memory: MemoryRecord) -> MemoryRecord:
        self.items[memory.memory_id] = memory
        return memory

    def get_memory(self, memory_id: str, scope=None) -> MemoryRecord | None:
        memory = self.items.get(memory_id)
        if memory is None:
            return None
        if scope is not None and memory.scope != scope:
            return None
        return memory

    def list_memories(self, scope=None) -> Sequence[MemoryRecord]:
        if scope is None:
            return list(self.items.values())
        return [memory for memory in self.items.values() if memory.scope == scope]

    def update_memory(self, memory: MemoryRecord) -> MemoryRecord:
        self.items[memory.memory_id] = memory
        return memory

    def update_status(self, memory_id: str, status: str) -> None:
        memory = self.items[memory_id]
        self.items[memory_id] = memory.model_copy(update={"status": status})


class ScriptedLLM(LLMProvider):
    def __init__(self, scripts: list[LLMResponse]) -> None:
        self.scripts = list(scripts)
        self.requests: list[LLMRequest] = []

    def complete(self, request: LLMRequest) -> LLMResponse:
        self.requests.append(request)
        return self.scripts.pop(0)

    def check_health(self) -> ProviderHealth:
        return ProviderHealth(name="test", status=ProviderHealthStatus.HEALTHY)

    def capabilities(self) -> ProviderCapabilities:
        return ProviderCapabilities(chat=True, tool_calling=True, structured_output=True)


def _final(text: str = "done") -> LLMResponse:
    return LLMResponse(text=text, provider_name="test", finish_reason="stop")


def _agent(repository: MemoryRepository, scripts: list[LLMResponse]) -> AgenticLLMProvider:
    registry = ToolRegistry()
    registry.register(MemoryWriteTool(repository))
    registry.register(MemorySearchTool(repository))
    executor = ToolExecutor(registry=registry, max_calls_per_execution=4)
    return AgenticLLMProvider(ScriptedLLM(scripts), registry, executor)


def _request(user_id: str, text: str) -> LLMRequest:
    principal = Principal(principal_id=user_id)
    return LLMRequest(
        prompt=text,
        messages=[{"role": "user", "content": text}],
        metadata={"_trusted_principal": principal, "conversation_id": f"conversation-{user_id}"},
    )


def test_model_selected_memory_write_persists_only_information() -> None:
    repository = InMemoryMemoryRepository()
    model = ScriptedLLM([
        LLMResponse(
            text="",
            provider_name="test",
            finish_reason="tool_calls",
            tool_calls=[LLMToolCall(id="call-1", name="memory.write", arguments={"content": "من پایتون را دوست دارم.", "kind": "user"})],
        ),
        _final("ذخیره شد."),
    ])
    agent = _agent(repository, model.scripts)

    response = agent.complete(_request("user-A", "این اطلاعات رو ذخیره کن: من پایتون را دوست دارم."))

    assert response.text == "ذخیره شد."
    assert response.metadata["tools_used"] is True
    saved = next(iter(repository.items.values()))
    assert saved.content == "من پایتون را دوست دارم."
    assert "این اطلاعات رو ذخیره کن" not in saved.content
    assert saved.scope is not None
    assert saved.scope.owner_id == "user-A"
    assert saved.scope.conversation_id == "conversation-user-A"


def test_model_selected_memory_search_reads_only_callers_scope() -> None:
    repository = InMemoryMemoryRepository()
    writer = MemoryWriteTool(repository)
    context_a = ToolExecutionContext(principal_id="user-A", conversation_id="conversation-user-A")
    context_b = ToolExecutionContext(principal_id="user-B", conversation_id="conversation-user-B")

    result = writer.execute(
        ToolCall(tool_call_id="seed", tool_name="memory.write", arguments={"content": "من پایتون را دوست دارم.", "kind": "user"}),
        context_a,
    )
    assert result.status == ToolExecutionStatus.SUCCESS

    registry = ToolRegistry()
    registry.register(MemorySearchTool(repository))
    executor = ToolExecutor(registry=registry, max_calls_per_execution=4)

    model_a = ScriptedLLM([
        LLMResponse(tool_calls=[LLMToolCall(id="search-a", name="memory.search", arguments={"query": "پایتون"})], provider_name="test", finish_reason="tool_calls"),
        _final("شما پایتون را دوست دارید."),
    ])
    agent_a = AgenticLLMProvider(model_a, registry, executor)
    response_a = agent_a.complete(_request("user-A", "من چه زبان برنامه نویسی را دوست دارم؟"))
    assert response_a.text == "شما پایتون را دوست دارید."
    assert "پایتون" in model_a.requests[1].messages[-1]["content"]

    model_b = ScriptedLLM([
        LLMResponse(tool_calls=[LLMToolCall(id="search-b", name="memory.search", arguments={"query": "پایتون"})], provider_name="test", finish_reason="tool_calls"),
        _final("اطلاعاتی پیدا نشد."),
    ])
    agent_b = AgenticLLMProvider(model_b, registry, executor)
    response_b = agent_b.complete(_request("user-B", "من چه زبان برنامه نویسی را دوست دارم؟"))
    assert response_b.text == "اطلاعاتی پیدا نشد."
    assert "پایتون" not in model_b.requests[1].messages[-1]["content"]


def test_model_cannot_override_principal_scope() -> None:
    repository = InMemoryMemoryRepository()
    registry = ToolRegistry()
    registry.register(MemoryWriteTool(repository))
    executor = ToolExecutor(registry=registry, max_calls_per_execution=4)
    model = ScriptedLLM([
        LLMResponse(
            tool_calls=[LLMToolCall(id="attack", name="memory.write", arguments={"content": "secret", "owner_id": "user-B"})],
            provider_name="test",
            finish_reason="tool_calls",
        ),
        _final("rejected"),
    ])
    agent = AgenticLLMProvider(model, registry, executor)

    response = agent.complete(_request("user-A", "save this"))

    assert response.text == "rejected"
    assert repository.items == {}
