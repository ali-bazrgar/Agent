from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any

from superagent.models.domain import MemoryKind, MemoryRecord, Source
from superagent.repositories.ports import MemoryRepository
from superagent.tools.models import ToolCall, ToolDefinition, ToolExecutionContext, ToolExecutionStatus, ToolResult
from superagent.tools.ports import ToolProvider


class MemoryWriteTool(ToolProvider):
    """Explicit persistence capability exposed to the model as a tool."""

    @property
    def definition(self) -> ToolDefinition:
        return ToolDefinition(
            name="memory.write",
            description=(
                "Persist information the user wants the assistant to remember. "
                "Use semantic understanding of the request; do not require a specific phrase or language. "
                "Store only the information itself, not instructions such as 'remember this'."
            ),
            input_schema={
                "type": "object",
                "properties": {
                    "content": {"type": "string", "description": "The information to persist, without the user's storage instruction."},
                    "kind": {"type": "string", "enum": ["user", "semantic", "procedural", "episodic"], "description": "Best semantic memory category."},
                    "importance": {"type": "number", "minimum": 0, "maximum": 1, "default": 0.7},
                },
                "required": ["content"],
                "additionalProperties": False,
            },
            output_schema={"type": "object", "properties": {"success": {"type": "boolean"}, "memory_id": {"type": "string"}, "status": {"type": "string"}}},
        )

    def __init__(self, repository: MemoryRepository) -> None:
        self.repository = repository

    def execute(self, call: ToolCall, context: ToolExecutionContext | None = None) -> ToolResult:
        content = call.arguments.get("content")
        if not isinstance(content, str) or not content.strip():
            return ToolResult(tool_call_id=call.tool_call_id, tool_name=call.tool_name, status=ToolExecutionStatus.INVALID_ARGUMENTS, error="content must be a non-empty string")
        kind_value = call.arguments.get("kind", MemoryKind.SEMANTIC.value)
        try:
            kind = MemoryKind(str(kind_value))
        except ValueError:
            return ToolResult(tool_call_id=call.tool_call_id, tool_name=call.tool_name, status=ToolExecutionStatus.INVALID_ARGUMENTS, error=f"unsupported memory kind: {kind_value}")
        importance = call.arguments.get("importance", 0.7)
        try:
            importance = min(1.0, max(0.0, float(importance)))
        except (TypeError, ValueError):
            return ToolResult(tool_call_id=call.tool_call_id, tool_name=call.tool_name, status=ToolExecutionStatus.INVALID_ARGUMENTS, error="importance must be a number")
        execution_id = context.execution_id if context else None
        now = datetime.now(timezone.utc)
        memory_id = f"mem-{uuid.uuid4().hex[:16]}"
        memory = MemoryRecord(
            memory_id=memory_id,
            kind=kind,
            content=content.strip(),
            classification="explicit",
            confidence=1.0,
            importance=importance,
            relevance=1.0,
            source=Source(source_id=memory_id, source_type="agent_tool", uri=execution_id, metadata={"tool_call_id": call.tool_call_id}),
            provenance=execution_id,
            created_at=now,
            updated_at=now,
        )
        try:
            self.repository.create_memory(memory)
        except Exception as exc:
            return ToolResult(tool_call_id=call.tool_call_id, tool_name=call.tool_name, status=ToolExecutionStatus.ERROR, error=f"memory persistence failed: {exc}")
        return ToolResult(
            tool_call_id=call.tool_call_id,
            tool_name=call.tool_name,
            status=ToolExecutionStatus.SUCCESS,
            output={"success": True, "memory_id": memory_id, "status": "persisted", "content": memory.content},
        )


class MemorySearchTool(ToolProvider):
    """Search persisted memories without language-specific trigger rules."""

    @property
    def definition(self) -> ToolDefinition:
        return ToolDefinition(
            name="memory.search",
            description="Search the user's persistent memories when answering requires remembering prior user information.",
            input_schema={
                "type": "object",
                "properties": {"query": {"type": "string", "description": "Natural-language description of the memory to find."}, "limit": {"type": "integer", "minimum": 1, "maximum": 20, "default": 5}},
                "required": ["query"],
                "additionalProperties": False,
            },
        )

    def __init__(self, repository: MemoryRepository) -> None:
        self.repository = repository

    def execute(self, call: ToolCall, context: ToolExecutionContext | None = None) -> ToolResult:
        query = call.arguments.get("query")
        if not isinstance(query, str) or not query.strip():
            return ToolResult(tool_call_id=call.tool_call_id, tool_name=call.tool_name, status=ToolExecutionStatus.INVALID_ARGUMENTS, error="query must be a non-empty string")
        try:
            memories = list(self.repository.list_memories())
            terms = {part.casefold() for part in query.split() if len(part.strip()) > 1}
            scored: list[tuple[int, MemoryRecord]] = []
            for memory in memories:
                haystack = memory.content.casefold()
                score = sum(1 for term in terms if term in haystack)
                if score:
                    scored.append((score, memory))
            scored.sort(key=lambda item: (-item[0], -item[1].importance, item[1].created_at))
            limit = min(20, max(1, int(call.arguments.get("limit", 5))))
            output = [{"memory_id": m.memory_id, "kind": m.kind.value, "content": m.content, "importance": m.importance} for _, m in scored[:limit]]
            return ToolResult(tool_call_id=call.tool_call_id, tool_name=call.tool_name, status=ToolExecutionStatus.SUCCESS, output={"matches": output})
        except Exception as exc:
            return ToolResult(tool_call_id=call.tool_call_id, tool_name=call.tool_name, status=ToolExecutionStatus.ERROR, error=f"memory search failed: {exc}")
