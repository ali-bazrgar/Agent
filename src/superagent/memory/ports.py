from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Sequence

from superagent.memory.models import ConsolidationResult, MemoryCandidate
from superagent.models.domain import MemoryKind, MemoryRecord, MemoryScope


class MemoryExtractorPort(ABC):
    """Port for extracting candidate memories from conversation messages."""

    @abstractmethod
    def extract_candidates(
        self,
        user_message: str,
        assistant_message: str,
        execution_id: str | None = None,
    ) -> list[MemoryCandidate]: ...


class MemoryConsolidatorPort(ABC):
    """Port for deduplicating, merging, or updating existing memories."""

    @abstractmethod
    def consolidate(
        self,
        candidate: MemoryCandidate,
        existing_memories: Sequence[MemoryRecord],
    ) -> ConsolidationResult: ...


class MemoryLifecyclePort(ABC):
    """Port for processing complete memory lifecycle post-execution."""

    @abstractmethod
    def process_interaction(
        self,
        user_message: str,
        assistant_message: str,
        execution_id: str | None = None,
        *,
        scope: MemoryScope | None = None,
        enable_heuristic_extraction: bool = False,
    ) -> list[MemoryRecord]: ...
