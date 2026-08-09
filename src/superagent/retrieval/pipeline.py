from __future__ import annotations

import time

from superagent.context.budget import TokenEstimator
from superagent.core.errors import ProviderError, ValidationError
from superagent.providers.contracts import EmbeddingProvider, EmbeddingRequest, RerankerProvider, RerankRequest
from superagent.retrieval.fusion import ReciprocalRankFusion
from superagent.retrieval.models import RetrievalCandidate, RetrievalQuery, RetrievalResult
from superagent.retrieval.ports import CandidateFusion, DenseRetriever, LexicalRetriever


class HybridRetriever:
    """Hybrid retrieval pipeline with optional reranking and token-aware final selection."""

    def __init__(
        self,
        embedding_provider: EmbeddingProvider,
        dense_retriever: DenseRetriever,
        lexical_retriever: LexicalRetriever,
        fusion: CandidateFusion | None = None,
        reranker_provider: RerankerProvider | None = None,
        token_estimator: TokenEstimator | None = None,
    ) -> None:
        self.embedding_provider = embedding_provider
        self.dense_retriever = dense_retriever
        self.lexical_retriever = lexical_retriever
        self.fusion = fusion or ReciprocalRankFusion()
        self.reranker_provider = reranker_provider
        self.token_estimator = token_estimator or TokenEstimator()

    def retrieve(self, query: RetrievalQuery) -> RetrievalResult:
        if not query.text or not query.text.strip():
            raise ValidationError("Retrieval query text cannot be empty or blank")

        start_time = time.perf_counter()

        embed_response = self.embedding_provider.embed(EmbeddingRequest(texts=[query.text]))
        if not embed_response.embeddings or not embed_response.embeddings[0]:
            raise ValidationError("Embedding provider returned empty query vector")

        query_vector = embed_response.embeddings[0]

        dense_candidates = self.dense_retriever.retrieve_dense(
            query_vector=query_vector,
            top_k=query.candidate_k,
            filters=query.filters,
        )
        lexical_candidates = self.lexical_retriever.retrieve_lexical(
            query_text=query.text,
            top_k=query.candidate_k,
            filters=query.filters,
        )
        fused_candidates = self.fusion.fuse_candidates(
            dense_candidates=dense_candidates,
            lexical_candidates=lexical_candidates,
            top_k=query.candidate_k,
        )

        should_rerank = query.rerank_config.enabled if query.rerank_config is not None else self.reranker_provider is not None
        reranked = False
        candidates = fused_candidates

        if should_rerank and self.reranker_provider is not None and fused_candidates:
            rerank_top_n = (
                query.rerank_config.top_n
                if query.rerank_config and query.rerank_config.top_n
                else query.candidate_k
            )
            to_rerank = fused_candidates[:rerank_top_n]
            remainder = fused_candidates[rerank_top_n:]

            try:
                rerank_res = self.reranker_provider.rerank(
                    RerankRequest(query=query.text, candidates=[c.content for c in to_rerank])
                )
                reranked_candidates: list[RetrievalCandidate] = []
                for item in rerank_res.ranked_items:
                    idx = item.get("index")
                    score = item.get("score", 0.0)
                    if isinstance(idx, int) and 0 <= idx < len(to_rerank):
                        cand = to_rerank[idx]
                        reranked_candidates.append(
                            cand.model_copy(
                                update={
                                    "retrieval_score": float(score),
                                    "reranker_score": float(score),
                                }
                            )
                        )

                seen_chunk_ids = {c.chunk_id for c in reranked_candidates}
                reranked_candidates.extend(c for c in to_rerank if c.chunk_id not in seen_chunk_ids)
                reranked_candidates.sort(key=lambda c: (-c.retrieval_score, c.chunk_id))
                candidates = reranked_candidates + remainder
                reranked = True
            except ProviderError:
                candidates = fused_candidates

        final_candidates = self._select_with_token_budget(candidates, query)
        duration_ms = (time.perf_counter() - start_time) * 1000.0
        estimated_tokens = sum(self.token_estimator.estimate_text(c.content) + 4 for c in final_candidates)

        return RetrievalResult(
            query=query.text,
            candidates=final_candidates,
            total_candidates=len(final_candidates),
            dense_count=len(dense_candidates),
            lexical_count=len(lexical_candidates),
            fused_count=len(fused_candidates),
            reranked=reranked,
            token_budget=query.token_budget,
            estimated_tokens=estimated_tokens,
            duration_ms=round(duration_ms, 2),
        )

    def _select_with_token_budget(
        self,
        candidates: list[RetrievalCandidate],
        query: RetrievalQuery,
    ) -> list[RetrievalCandidate]:
        selected: list[RetrievalCandidate] = []
        used_tokens = 0
        for candidate in candidates:
            if len(selected) >= query.top_k:
                break
            candidate_tokens = self.token_estimator.estimate_text(candidate.content) + 4
            if query.token_budget is not None and used_tokens + candidate_tokens > query.token_budget:
                continue
            selected.append(candidate)
            used_tokens += candidate_tokens
        return selected
