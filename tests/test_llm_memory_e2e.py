from __future__ import annotations

from typing import Sequence

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
from superagent.tools.models import ToolCall
from superagent.tools.registry import ToolRegistry


class InMemoryMemoryRepository(MemoryRepository):
    def __init__(self) -> None:
        self.items: dict[str, MemoryRecord] = {}

    def create_memory(self, memory: MemoryRecord) -> MemoryRecord:
        self.items[memory.memory_id] = memory
        return memory

    def get_memory(self, memory_id: str) -> MemoryRecord | None:
        return self.items.get(memory_id)

    def list_memories(self) -> Sequence[MemoryRecord]:
        return list(self.items.values())

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


def test_model_selected_memory_write_persists_only_information() -> None:
    repository = InMemoryMemoryRepository()
    registry = ToolRegistry()
    registry.register(MemoryWriteTool(repository))
    executor = ToolExecutor(registry=registry, max_calls_per_execution=4)
    model = ScriptedLLM([
        LLMResponse(
            text="",
            provider_name="test",
            finish_reason="tool_calls",
            tool_calls=[LLMToolCall(id="call-1", name="memory.write", arguments={"content": "من پایتون را دوست دارم.", "kind": "user"})],
        ),
        _final("ذخیره شد."),
    ])
    agent = AgenticLLMProvider(model, registry, executor)

    response = agent.complete(LLMRequest(
        prompt="این اطلاعات رو ذخیره کن: من پایتون را دوست دارم.",
        messages=[{"role": "user", "content": "این اطلاعات رو ذخیره کن: من پایتون را دوست دارم."}],
    ))

    assert response.text == "ذخیره شد."
    assert response.metadata["tools_used"] is True
    assert [item.content for item in repository.items.values()] == ["من پایتون را دوست دارم."]
    assert "این اطلاعات رو ذخیره کن" not in next(iter(repository.items.values())).content
    assert model.requests[0].tools
    assert model.requests[0].tools[0]["function"]["name"] == "memory.write"


def test_model_selected_memory_search_reads_persistent_memory() -> None:
    repository = InMemoryMemoryRepository()
    MemoryWriteTool(repository).execute(
        call=ToolCall(
            tool_call_id="seed",
            tool_name="memory.write",
            arguments={"content": "من پایتون را دوست دارم.", "kind": "user"},
        )
    )
    registry = ToolRegistry()
    registry.register(MemorySearchTool(repository))
    executor = ToolExecutor(registry=registry, max_calls_per_execution=4)
    model = ScriptedLLM([
        LLMResponse(
            text="",
            provider_name="test",
            finish_reason="tool_calls",
            tool_calls=[LLMToolCall(id="call-1", name="memory.search", arguments={"query": "پایتون"})],
        ),
        _final("شما پایتون را دوست دارید."),
    ])
    agent = AgenticLLMProvider(model, registry, executor)

    response = agent.complete(LLMRequest(
        prompt="من چه زبان برنامه نویسی را دوست دارم؟",
        messages=[{"role": "user", "content": "من چه زبان برنامه نویسی را دوست دارم؟"}],
    ))

    assert response.text == "شما پایتون را دوست دارید."
    assert response.metadata["tools_used"] is True
    assert model.requests[1].messages[-1]["role"] == "tool"
    assert "پایتون" in model.requests[1].messages[-1]["content"]
