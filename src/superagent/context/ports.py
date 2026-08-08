from __future__ import annotations

from abc import ABC, abstractmethod

from superagent.context.models import ContextBuildResult, ContextRequest
from superagent.models.domain import MemoryKind, MemoryRecord


class MemoryRetrieverPort(ABC):
    """Port for retrieving relevant memories for context assembly."""

    @abstractmethod
    def retrieve_memories(
        self,
        query_text: str,
        top_k: int = 10,
        kinds: list[MemoryKind] | None = None,
    ) -> list[MemoryRecord]: ...


class ContextEnginePort(ABC):
    """Port for Context Engine context construction."""

    @abstractmethod
    def build_context(self, request: ContextRequest) -> ContextBuildResult: ...
