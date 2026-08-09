from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Protocol, Sequence

from superagent.retrieval.models import RetrievalCandidate, RetrievalFilter, RetrievalQuery, RetrievalResult
from superagent.retrieval.pipeline import HybridRetriever


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


@dataclass(frozen=True)
class RetrievalDiagnostics:
    """Observability information about an orchestration decision."""

    requested_sources: tuple[RetrievalSource, ...]
    executed_sources: tuple[RetrievalSource, ...]
    failed_sources: tuple[RetrievalSource, ...]
    candidate_counts: dict[str, int]
    total_candidates: int


@dataclass(frozen=True)
class OrchestratedRetrievalResult:
    """Merged result returned to the context assembly layer."""

    candidates: tuple[RetrievalCandidate, ...]
    diagnostics: RetrievalDiagnostics


class RetrievalOrchestrator:
    """Coordinate retrieval across logical sources without knowing storage details.

    The orchestrator deliberately does not depend on Qdrant, SQLite, a particular
    embedding model, or a particular reranker. Each source is supplied as a backend.
    """

    def __init__(self, backends: dict[RetrievalSource, RetrievalSourceBackend]) -> None:
        self.backends = dict(backends)

    def retrieve(
        self,
        query: str,
        *,
        sources: Sequence[RetrievalSource],
        top_k: int = 10,
        candidate_k: int = 20,
        filters: RetrievalFilter | None = None,
        rerank_config=None,
    ) -> OrchestratedRetrievalResult:
        if not query or not query.strip():
            raise ValueError("Retrieval query cannot be empty")
        if top_k < 1:
            raise ValueError("top_k must be at least 1")
        if candidate_k < top_k:
            raise ValueError("candidate_k must be greater than or equal to top_k")

        requested = tuple(dict.fromkeys(sources))
        executed: list[RetrievalSource] = []
        failed: list[RetrievalSource] = []
        counts: dict[str, int] = {}
        merged: list[RetrievalCandidate] = []

        per_source_k = max(1, candidate_k // max(1, len(requested)))
        for source in requested:
            backend = self.backends.get(source)
            if backend is None:
                failed.append(source)
                counts[source.value] = 0
                continue

            try:
                result = backend.retrieve(
                    RetrievalQuery(
                        text=query,
                        top_k=per_source_k,
                        candidate_k=max(per_source_k, top_k),
                        filters=filters,
                        rerank_config=rerank_config,
                    )
                )
            except Exception:
                # A single optional source must not make unrelated sources unusable.
                failed.append(source)
                counts[source.value] = 0
                continue

            executed.append(source)
            counts[source.value] = len(result.candidates)
            for candidate in result.candidates:
                provenance = dict(candidate.provenance)
                provenance.setdefault("retrieval_source", source.value)
                merged.append(candidate.model_copy(update={"provenance": provenance}))

        # Stable deterministic de-duplication. If the same chunk is available from
        # several logical sources, retain the highest retrieval score.
        best_by_chunk: dict[str, RetrievalCandidate] = {}
        for candidate in merged:
            previous = best_by_chunk.get(candidate.chunk_id)
            if previous is None or candidate.retrieval_score > previous.retrieval_score:
                best_by_chunk[candidate.chunk_id] = candidate

        final = sorted(
            best_by_chunk.values(),
            key=lambda item: (-item.retrieval_score, item.chunk_id),
        )[:top_k]

        diagnostics = RetrievalDiagnostics(
            requested_sources=requested,
            executed_sources=tuple(executed),
            failed_sources=tuple(failed),
            candidate_counts=counts,
            total_candidates=len(merged),
        )
        return OrchestratedRetrievalResult(candidates=tuple(final), diagnostics=diagnostics)


def hybrid_backend(retriever: HybridRetriever) -> RetrievalSourceBackend:
    """Adapt the existing hybrid retriever to the orchestration contract."""

    return retriever
