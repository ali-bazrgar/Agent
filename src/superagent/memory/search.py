from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone

from superagent.models.domain import MemoryKind, MemoryRecord, MemoryStatus
from superagent.repositories.ports import MemoryRepository


@dataclass(frozen=True)
class MemorySearchQuery:
    text: str
    limit: int = 10
    token_budget: int | None = None
    kinds: tuple[MemoryKind, ...] = ()
    min_importance: float = 0.0

    def __post_init__(self) -> None:
        if not self.text.strip():
            raise ValueError("Memory query cannot be empty")
        if self.limit < 1:
            raise ValueError("limit must be at least 1")
        if self.token_budget is not None and self.token_budget < 1:
            raise ValueError("token_budget must be at least 1 when provided")
        if not 0.0 <= self.min_importance <= 1.0:
            raise ValueError("min_importance must be between 0 and 1")


@dataclass(frozen=True)
class MemorySearchHit:
    memory: MemoryRecord
    score: float
    estimated_tokens: int


@dataclass(frozen=True)
class MemorySearchResult:
    hits: tuple[MemorySearchHit, ...]
    estimated_tokens: int


class MemorySearchService:
    """Retrieve active memories using relevance, confidence, importance and recency.

    This is deliberately persistence-agnostic above the repository port and enforces
    the retrieval token budget before memories are returned to context assembly.
    """

    def __init__(self, repository: MemoryRepository) -> None:
        self.repository = repository

    def search(self, query: MemorySearchQuery) -> MemorySearchResult:
        terms = {term for term in query.text.casefold().split() if term}
        allowed = set(query.kinds)
        now = datetime.now(timezone.utc)
        scored: list[tuple[float, MemoryRecord]] = []

        for memory in self.repository.list_memories():
            if memory.status is not MemoryStatus.ACTIVE:
                continue
            if allowed and memory.kind not in allowed:
                continue
            if memory.importance < query.min_importance:
                continue

            content = memory.content.casefold()
            overlap = (
                sum(1 for term in terms if term in content) / max(1, len(terms))
                if terms
                else 0.0
            )
            reference_time = memory.last_accessed_at or memory.updated_at
            age_days = max(0.0, (now - reference_time).total_seconds() / 86400.0)
            recency = 1.0 / (1.0 + age_days / 30.0)
            score = (
                0.45 * overlap
                + 0.25 * memory.confidence
                + 0.20 * memory.importance
                + 0.10 * recency
            )
            scored.append((round(score, 6), memory))

        scored.sort(key=lambda item: (-item[0], -item[1].updated_at.timestamp(), item[1].memory_id))

        hits: list[MemorySearchHit] = []
        used_tokens = 0
        for score, memory in scored:
            if len(hits) >= query.limit:
                break
            tokens = self._estimate_tokens(memory.content)
            if query.token_budget is not None and used_tokens + tokens > query.token_budget:
                continue
            hits.append(MemorySearchHit(memory=memory, score=score, estimated_tokens=tokens))
            used_tokens += tokens

        return MemorySearchResult(hits=tuple(hits), estimated_tokens=used_tokens)

    @staticmethod
    def _estimate_tokens(content: str) -> int:
        return max(1, (len(content) + 3) // 4)
