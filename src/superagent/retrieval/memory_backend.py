from __future__ import annotations

from superagent.memory.search import MemorySearchQuery, MemorySearchService
from superagent.models.domain import MemoryKind
from superagent.retrieval.models import RetrievalCandidate, RetrievalQuery, RetrievalResult


class MemoryRetrievalBackend:
    """Adapt the domain MemorySearchService to the generic retrieval backend port."""

    def __init__(self, search: MemorySearchService) -> None:
        self.search = search

    def retrieve(self, query: RetrievalQuery) -> RetrievalResult:
        filters = query.filters
        kinds = ()
        min_importance = 0.0
        if filters is not None:
            if filters.memory_kinds:
                try:
                    kinds = tuple(MemoryKind(value) for value in filters.memory_kinds)
                except ValueError as exc:
                    raise ValueError(f"Unknown memory kind: {exc}") from exc
            if filters.memory_min_importance is not None:
                min_importance = filters.memory_min_importance

        memory_result = self.search.search(
            MemorySearchQuery(
                text=query.text,
                limit=query.top_k,
                token_budget=query.token_budget,
                kinds=kinds,
                min_importance=min_importance,
            )
        )

        candidates = [
            RetrievalCandidate(
                chunk_id=f"memory:{hit.memory.memory_id}",
                document_id=f"memory:{hit.memory.memory_id}",
                version_id=None,
                source_id=hit.memory.source.source_id,
                content=hit.memory.content,
                retrieval_method="memory",
                retrieval_score=hit.score,
                dense_score=None,
                lexical_score=None,
                fused_score=hit.score,
                reranker_score=None,
                chunk_index=0,
                metadata={
                    "memory_kind": hit.memory.kind.value,
                    "memory_status": hit.memory.status.value,
                    "importance": hit.memory.importance,
                    "confidence": hit.memory.confidence,
                    "relevance": hit.memory.relevance,
                },
                provenance={
                    "retrieval_source": "memory",
                    "memory_id": hit.memory.memory_id,
                    "memory_created_at": hit.memory.created_at.isoformat(),
                    "memory_updated_at": hit.memory.updated_at.isoformat(),
                },
            )
            for hit in memory_result.hits
        ]

        return RetrievalResult(
            query=query.text,
            candidates=candidates,
            total_candidates=len(candidates),
            reranked=False,
            token_budget=query.token_budget,
            estimated_tokens=memory_result.estimated_tokens,
        )
