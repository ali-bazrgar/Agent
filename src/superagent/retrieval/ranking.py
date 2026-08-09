from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Sequence

from superagent.retrieval.models import RetrievalCandidate


@dataclass(frozen=True)
class GlobalRankingConfig:
    """Weights for normalizing heterogeneous source scores."""

    relevance_weight: float = 0.55
    confidence_weight: float = 0.20
    provenance_weight: float = 0.10
    source_priority_weight: float = 0.15

    def __post_init__(self) -> None:
        values = (
            self.relevance_weight,
            self.confidence_weight,
            self.provenance_weight,
            self.source_priority_weight,
        )
        if any(value < 0 for value in values):
            raise ValueError("ranking weights cannot be negative")
        if sum(values) <= 0:
            raise ValueError("at least one ranking weight must be positive")


@dataclass(frozen=True)
class RankedCandidate:
    candidate: RetrievalCandidate
    global_score: float
    estimated_tokens: int


class GlobalRetrievalRanker:
    """Normalize and rank candidates produced by heterogeneous retrieval sources."""

    def __init__(
        self,
        *,
        config: GlobalRankingConfig | None = None,
        source_priority: dict[str, float] | None = None,
        tokenizer: Callable[[str], int] | None = None,
    ) -> None:
        self.config = config or GlobalRankingConfig()
        self.source_priority = source_priority or {}
        self.tokenizer = tokenizer

    def rank(self, candidates: Sequence[RetrievalCandidate]) -> tuple[RankedCandidate, ...]:
        ranked: list[RankedCandidate] = []
        for candidate in candidates:
            metadata = candidate.metadata
            source = str(candidate.provenance.get("retrieval_source", candidate.retrieval_method))
            relevance = self._clamp(candidate.reranker_score if candidate.reranker_score is not None else candidate.retrieval_score)
            confidence = self._clamp(float(metadata.get("confidence", 1.0)))
            provenance = 1.0 if candidate.provenance else 0.0
            priority = self._clamp(float(self.source_priority.get(source, 0.5)))
            score = (
                self.config.relevance_weight * relevance
                + self.config.confidence_weight * confidence
                + self.config.provenance_weight * provenance
                + self.config.source_priority_weight * priority
            ) / (
                self.config.relevance_weight
                + self.config.confidence_weight
                + self.config.provenance_weight
                + self.config.source_priority_weight
            )
            ranked.append(
                RankedCandidate(
                    candidate=candidate,
                    global_score=score,
                    estimated_tokens=self._estimate(candidate.content),
                )
            )
        return tuple(sorted(ranked, key=lambda item: (-item.global_score, item.candidate.chunk_id)))

    def select_with_budget(
        self,
        candidates: Sequence[RetrievalCandidate],
        *,
        token_budget: int | None,
        top_k: int,
    ) -> tuple[RankedCandidate, ...]:
        if top_k < 1:
            raise ValueError("top_k must be at least 1")
        if token_budget is not None and token_budget < 1:
            raise ValueError("token_budget must be at least 1 when provided")

        ranked = self.rank(candidates)
        selected: list[RankedCandidate] = []
        used = 0
        for item in ranked:
            if len(selected) >= top_k:
                break
            if token_budget is not None and used + item.estimated_tokens > token_budget:
                continue
            selected.append(item)
            used += item.estimated_tokens
        return tuple(selected)

    def _estimate(self, text: str) -> int:
        if self.tokenizer is not None:
            return max(1, int(self.tokenizer(text)))
        return max(1, (len(text) + 3) // 4)

    @staticmethod
    def _clamp(value: float) -> float:
        return max(0.0, min(1.0, value))
