from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Protocol, Sequence

from superagent.retrieval.models import (
    RetrievalCandidate,
    RetrievalFilter,
    RetrievalQuery,
    RetrievalResult,
    RerankConfig,
)
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
        # token_budget is a global orchestration constraint. Passing it to each
        # backend when multiple sources are active would incorrectly make every
        # backend believe it owns the full budget. A single-source query may use
        # the budget as a backend optimization hint because there is no competing
        # source, while the global ranker remains authoritative.
        backend_token_budget = token_budget if len(requested) == 1 else None
        budgets: dict[str, int | None] = {
            source.value: backend_token_budget for source in requested
        }
        estimated: dict[str, int] = {}
        merged: list[RetrievalCandidate] = []

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
                        candidate_k=candidate_k,
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
        # the global context budget twice. The priority deliberately uses only
        # fields that are part of RetrievalCandidate's canonical schema. In
        # particular, do not invent a generic `confidence`/`rerank_score` field:
        # reranking is represented by `reranker_score` and source retrieval by
        # `retrieval_score`.
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
    def _candidate_priority(candidate: RetrievalCandidate) -> tuple[float, float, float, float, str]:
        """Return a deterministic, schema-safe priority for duplicate chunks.

        Prefer an explicit reranker score when available, then fused retrieval
        score, then the base retrieval score. Dense/lexical scores are only
        used as additional deterministic tie-breakers. No score is synthesized
        from fields that do not exist on the domain model.
        """

        return (
            candidate.reranker_score if candidate.reranker_score is not None else float("-inf"),
            candidate.fused_score if candidate.fused_score is not None else float("-inf"),
            candidate.retrieval_score,
            candidate.dense_score if candidate.dense_score is not None else float("-inf"),
            candidate.chunk_id,
        )
