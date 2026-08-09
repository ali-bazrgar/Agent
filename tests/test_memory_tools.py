from __future__ import annotations

from superagent.memory import MemoryConsolidator, MemoryExtractor, MemoryLifecycle
from superagent.models.domain import MemoryKind, MemoryRecord
from superagent.tools.memory import MemorySearchTool, MemoryWriteTool
from superagent.tools.models import ToolCall, ToolExecutionContext, ToolExecutionStatus


class InMemoryRepository:
    def __init__(self) -> None:
        self.items: dict[str, MemoryRecord] = {}

    def create_memory(self, memory: MemoryRecord) -> MemoryRecord:
        self.items[memory.memory_id] = memory
        return memory

    def get_memory(self, memory_id: str) -> MemoryRecord | None:
        return self.items.get(memory_id)

    def list_memories(self):
        return list(self.items.values())

    def update_memory(self, memory: MemoryRecord) -> MemoryRecord:
        self.items[memory.memory_id] = memory
        return memory

    def mark_accessed(self, memory_id: str) -> None:
        pass

    def update_status(self, memory_id: str, status: str) -> None:
        self.items[memory_id] = self.items[memory_id].model_copy(update={"status": status})


def test_memory_write_tool_persists_only_content() -> None:
    repository = InMemoryRepository()
    tool = MemoryWriteTool(repository)

    result = tool.execute(
        ToolCall(tool_call_id="call-1", tool_name="memory.write", arguments={"content": "من پایتون را دوست دارم", "kind": "user"}),
        ToolExecutionContext(execution_id="exec-1"),
    )

    assert result.status == ToolExecutionStatus.SUCCESS
    assert len(repository.items) == 1
    memory = next(iter(repository.items.values()))
    assert memory.kind == MemoryKind.USER
    assert memory.content == "من پایتون را دوست دارم"
    assert "ذخیره" not in memory.content


def test_memory_search_tool_is_language_agnostic_at_interface_level() -> None:
    repository = InMemoryRepository()
    write = MemoryWriteTool(repository)
    write.execute(ToolCall(tool_call_id="write-1", tool_name="memory.write", arguments={"content": "I like Python", "kind": "user"}))

    result = MemorySearchTool(repository).execute(ToolCall(tool_call_id="search-1", tool_name="memory.search", arguments={"query": "Python"}))

    assert result.status == ToolExecutionStatus.SUCCESS
    assert result.output["matches"][0]["content"] == "I like Python"
