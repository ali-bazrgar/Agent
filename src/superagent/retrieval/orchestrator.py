from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Protocol, Sequence

from superagent.retrieval.models import RetrievalCandidate, RetrievalFilter, RetrievalQuery, RetrievalResult, RerankConfig
from superagent.retrieval.pipeline import HybridRetriever
from superagent.retrieval.ranking import GlobalRetrievalRanker


class RetrievalSource(str, Enum):
    """Logical knowledge sources an agent may retrieve from."""

    MEMORY = "memory"
    CONVERSATION = "conversation"
    KNOWLEDGE = "knowledge"
    DOCUMENT = "document"
    HYBRID = "hybrid"


class RetrievalSourceBackend(Protocol):
    """Provider-neutral backend for one logical retrieval source."""

    def retrieve(self, query: RetrievalQuery) -> RetrievalResult: ...


@dataclass(frozen=True)
class RetrievalSourceRequest:
    source: RetrievalSource
    backend: RetrievalSourceBackend
    candidate_budget: int
    token_budget: int | None = None


@dataclass(frozen=True)
class RetrievalDiagnostics:
    """Observability information about an orchestration decision."""

    requested_sources: tuple[RetrievalSource, ...]
    executed_sources: tuple[RetrievalSource, ...]
    failed_sources: tuple[RetrievalSource, ...]
    candidate_counts: dict[str, int]
    token_budgets: dict[str, int | None]
    estimated_tokens: dict[str, int]
    total_candidates: int
    total_estimated_tokens: int


@dataclass(frozen=True)
class OrchestratedRetrievalResult:
    """Merged and globally budgeted result returned to context assembly."""

    candidates: tuple[RetrievalCandidate, ...]
    diagnostics: RetrievalDiagnostics


class RetrievalOrchestrator:
    """Coordinate retrieval across logical sources without knowing storage details."""

    def __init__(
        self,
        backends: dict[RetrievalSource, RetrievalSourceBackend],
        *,
        ranker: GlobalRetrievalRanker | None = None,
    ) -> None:
        self.backends = dict(backends)
        self.ranker = ranker or GlobalRetrievalRanker()

    def retrieve(
        self,
        query: str,
        *,
        sources: Sequence[RetrievalSource],
        top_k: int = 10,
        candidate_k: int = 20,
        token_budget: int | None = None,
        filters: RetrievalFilter | None = None,
        rerank_config: RerankConfig | None = None,
    ) -> OrchestratedRetrievalResult:
        if not query or not query.strip():
            raise ValueError("Retrieval query cannot be empty")
        if top_k < 1:
            raise ValueError("top_k must be at least 1")
        if candidate_k < top_k:
            raise ValueError("candidate_k must be greater than or equal to top_k")
        if token_budget is not None and token_budget < 1:
            raise ValueError("token_budget must be at least 1 when provided")

        requested = tuple(dict.fromkeys(sources))
        if not requested:
            raise ValueError("At least one retrieval source is required")

        executed: list[RetrievalSource] = []
        failed: list[RetrievalSource] = []
        counts: dict[str, int] = {}
        # With multiple sources, token_budget is a global orchestration budget
        # and must remain invisible to individual backends until after merge,
        # deduplication and global ranking. Otherwise one source can consume or
        # prematurely truncate the shared budget before cross-source ranking.
        #
        # With exactly one source there is no cross-source competition, so the
        # same global budget can safely be forwarded as a backend optimization
        # hint. The final authoritative budget is still enforced by the global
        # ranker below.
        backend_token_budget = token_budget if len(requested) == 1 else None
        budgets: dict[str, int | None] = {
            source.value: backend_token_budget for source in requested
        }
        estimated: dict[str, int] = {}
        merged: list[RetrievalCandidate] = []

        per_source_k = max(top_k, candidate_k)

        for source in requested:
            backend = self.backends.get(source)
            if backend is None:
                failed.append(source)
                counts[source.value] = 0
                estimated[source.value] = 0
                continue

            try:
                result = backend.retrieve(
                    RetrievalQuery(
                        text=query,
                        top_k=top_k,
                        candidate_k=per_source_k,
                        token_budget=backend_token_budget,
                        filters=filters,
                        rerank_config=rerank_config,
                    )
                )
            except Exception:
                failed.append(source)
                counts[source.value] = 0
                estimated[source.value] = 0
                continue

            executed.append(source)
            counts[source.value] = len(result.candidates)
            estimated[source.value] = result.estimated_tokens
            for candidate in result.candidates:
                provenance = dict(candidate.provenance)
                provenance.setdefault("retrieval_source", source.value)
                merged.append(candidate.model_copy(update={"provenance": provenance}))

        # De-duplicate before global ranking so a repeated chunk cannot consume
        # global context budget twice.
        best_by_chunk: dict[str, RetrievalCandidate] = {}
        for candidate in merged:
            previous = best_by_chunk.get(candidate.chunk_id)
            if previous is None or self._candidate_priority(candidate) > self._candidate_priority(previous):
                best_by_chunk[candidate.chunk_id] = candidate

        selected = self.ranker.select_with_budget(
            tuple(best_by_chunk.values()),
            token_budget=token_budget,
            top_k=top_k,
        )
        final_candidates: list[RetrievalCandidate] = []
        for item in selected:
            candidate = item.candidate.model_copy(
                update={
                    "metadata": {
                        **item.candidate.metadata,
                        "global_score": item.global_score,
                        "global_estimated_tokens": item.estimated_tokens,
                    }
                }
            )
            final_candidates.append(candidate)

        final = tuple(final_candidates)
        total_estimated_tokens = sum(item.estimated_tokens for item in selected)

        diagnostics = RetrievalDiagnostics(
            requested_sources=requested,
            executed_sources=tuple(executed),
            failed_sources=tuple(failed),
            candidate_counts=counts,
            token_budgets=budgets,
            estimated_tokens=estimated,
            total_candidates=len(merged),
            total_estimated_tokens=total_estimated_tokens,
        )
        return OrchestratedRetrievalResult(candidates=final, diagnostics=diagnostics)

    @staticmethod
    def _candidate_priority(candidate: RetrievalCandidate) -> tuple[float, float, float, str]:
        return (
            candidate.retrieval_score,
            candidate.rerank_score if candidate.rerank_score is not None else float("-inf"),
            candidate.confidence if candidate.confidence is not None else float("-inf"),
            candidate.chunk_id,
        )
