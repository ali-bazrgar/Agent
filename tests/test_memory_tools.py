from __future__ import annotations

import pytest

from superagent.models.domain import MemoryScopeType
from superagent.tools.memory import MemorySearchTool, MemoryWriteTool
from superagent.tools.models import ToolCall, ToolExecutionContext, ToolExecutionStatus


class InMemoryRepository:
    def __init__(self) -> None:
        self.items = {}

    def create_memory(self, memory):
        self.items[memory.memory_id] = memory
        return memory

    def get_memory(self, memory_id, scope=None):
        memory = self.items.get(memory_id)
        if memory is None or scope is None or memory.scope != scope:
            return None
        return memory

    def list_memories(self, scope=None):
        if scope is None:
            return []
        return [memory for memory in self.items.values() if memory.scope == scope]

    def update_memory(self, memory):
        self.items[memory.memory_id] = memory
        return memory

    def update_status(self, memory_id, status):
        self.items[memory_id] = self.items[memory_id].model_copy(update={"status": status})


def context(user_id: str) -> ToolExecutionContext:
    return ToolExecutionContext(
        execution_id="exec-1",
        principal_id=user_id,
        conversation_id="conv-1",
    )


def test_memory_write_persists_trusted_runtime_scope() -> None:
    repository = InMemoryRepository()
    result = MemoryWriteTool(repository).execute(
        ToolCall(tool_call_id="write-1", tool_name="memory.write", arguments={"content": "I like Python", "kind": "user"}),
        context("user-A"),
    )

    assert result.status == ToolExecutionStatus.SUCCESS
    memory = next(iter(repository.items.values()))
    assert memory.scope is not None
    assert memory.scope.scope_type == MemoryScopeType.USER
    assert memory.scope.owner_id == "user-A"
    assert memory.scope.conversation_id == "conv-1"


def test_memory_search_isolated_by_runtime_scope() -> None:
    repository = InMemoryRepository()
    write = MemoryWriteTool(repository)
    write.execute(
        ToolCall(tool_call_id="write-1", tool_name="memory.write", arguments={"content": "I like Python", "kind": "user"}),
        context("user-A"),
    )

    own = MemorySearchTool(repository).execute(
        ToolCall(tool_call_id="search-a", tool_name="memory.search", arguments={"query": "Python"}),
        context("user-A"),
    )
    other = MemorySearchTool(repository).execute(
        ToolCall(tool_call_id="search-b", tool_name="memory.search", arguments={"query": "Python"}),
        context("user-B"),
    )

    assert own.status == ToolExecutionStatus.SUCCESS
    assert len(own.output["matches"]) == 1
    assert other.status == ToolExecutionStatus.SUCCESS
    assert other.output["matches"] == []


def test_model_cannot_override_memory_owner() -> None:
    repository = InMemoryRepository()
    result = MemoryWriteTool(repository).execute(
        ToolCall(
            tool_call_id="attack-1",
            tool_name="memory.write",
            arguments={"content": "Python", "owner_id": "user-B"},
        ),
        context("user-A"),
    )

    assert result.status == ToolExecutionStatus.SECURITY_REJECTED
    assert repository.items == {}


def test_memory_tools_require_trusted_scope() -> None:
    repository = InMemoryRepository()
    result = MemorySearchTool(repository).execute(
        ToolCall(tool_call_id="search-1", tool_name="memory.search", arguments={"query": "Python"}),
        ToolExecutionContext(execution_id="exec-1"),
    )

    assert result.status == ToolExecutionStatus.SECURITY_REJECTED
