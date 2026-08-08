from __future__ import annotations

from typing import Sequence

from superagent.context.ports import MemoryRetrieverPort
from superagent.models.domain import MemoryKind, MemoryRecord, MemoryStatus
from superagent.repositories.ports import MemoryRepository


class MemoryRanker:
    """Ranks memory records based on relevance, confidence, importance, and recency."""

    @staticmethod
    def score_memory(memory: MemoryRecord, query_terms: set[str]) -> float:
        if memory.status != MemoryStatus.ACTIVE:
            return 0.0

        content_lower = memory.content.lower()
        # Word overlap score
        matches = sum(1 for term in query_terms if term in content_lower)
        overlap_score = min(1.0, matches / max(1, len(query_terms))) if query_terms else 0.5

        # Base composite score
        base_score = (
            0.4 * overlap_score
            + 0.3 * memory.confidence
            + 0.2 * memory.importance
            + 0.1 * memory.relevance
        )
        return round(base_score, 4)

    @classmethod
    def rank_memories(
        self,
        memories: Sequence[MemoryRecord],
        query_text: str,
        top_k: int = 10,
        kinds: list[MemoryKind] | None = None,
    ) -> list[MemoryRecord]:
        query_terms = set(query_text.lower().split())
        allowed_kinds = set(kinds) if kinds else None

        scored: list[tuple[float, MemoryRecord]] = []
        for mem in memories:
            if mem.status != MemoryStatus.ACTIVE:
                continue
            if allowed_kinds and mem.kind not in allowed_kinds:
                continue
            score = self.score_memory(mem, query_terms)
            scored.append((score, mem))

        # Sort by score desc, then created_at desc
        scored.sort(key=lambda x: (x[0], x[1].created_at), reverse=True)
        return [mem for score, mem in scored[:top_k]]


class DefaultMemoryRetriever(MemoryRetrieverPort):
    """Adapter bridging MemoryRepository with MemoryRetrieverPort for ContextEngine."""

    def __init__(self, memory_repository: MemoryRepository) -> None:
        self.repository = memory_repository

    def retrieve_memories(
        self,
        query_text: str,
        top_k: int = 10,
        kinds: list[MemoryKind] | None = None,
    ) -> list[MemoryRecord]:
        all_memories = self.repository.list_memories()
        return MemoryRanker.rank_memories(
            memories=all_memories,
            query_text=query_text,
            top_k=top_k,
            kinds=kinds,
        )
