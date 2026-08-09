from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping

from superagent.context.request import Principal, RequestContext


@dataclass(frozen=True)
class MemoryToolContext:
    """Trusted runtime context for memory tools.

    Ownership and scope are supplied by the runtime, never by the model.
    """

    principal: Principal
    conversation_id: str
    execution_id: str
    project_id: str | None = None

    @classmethod
    def from_request(cls, context: RequestContext) -> "MemoryToolContext":
        return cls(
            principal=context.principal,
            conversation_id=context.conversation_id,
            execution_id=context.execution_id,
            project_id=context.metadata.get("project_id"),
        )


class MemoryToolValidationError(ValueError):
    """Raised when a model supplies runtime-owned memory fields."""


def _reject_runtime_owned_fields(arguments: Mapping[str, Any]) -> None:
    forbidden = {
        "owner_id",
        "user_id",
        "principal_id",
        "scope_type",
        "conversation_id",
        "project_id",
    }
    supplied = sorted(forbidden.intersection(arguments))
    if supplied:
        raise MemoryToolValidationError(
            "Runtime-owned fields must not be supplied by the model: "
            + ", ".join(supplied)
        )


def build_memory_write_scope(context: MemoryToolContext) -> dict[str, str | None]:
    """Build the trusted scope for a memory.write operation."""
    return {
        "scope_type": "user",
        "owner_id": context.principal.principal_id,
        "conversation_id": context.conversation_id,
        "project_id": context.project_id,
    }


def build_memory_search_scope(context: MemoryToolContext) -> dict[str, str | None]:
    """Build the trusted scope for a memory.search operation."""
    return {
        "scope_type": "user",
        "owner_id": context.principal.principal_id,
        "conversation_id": context.conversation_id,
        "project_id": context.project_id,
    }


def validate_memory_tool_arguments(arguments: Mapping[str, Any]) -> None:
    """Validate model arguments without allowing it to control ownership."""
    _reject_runtime_owned_fields(arguments)
