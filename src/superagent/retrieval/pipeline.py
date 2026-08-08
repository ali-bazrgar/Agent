from __future__ import annotations

import time

from superagent.core.errors import ProviderError, ValidationError
from superagent.providers.contracts import EmbeddingProvider, EmbeddingRequest, RerankerProvider, RerankRequest
from superagent.retrieval.dense import SqliteDenseRetriever
from superagent.retrieval.fusion import ReciprocalRankFusion
from superagent.retrieval.lexical import SqliteLexicalRetriever
from superagent.retrieval.models import RetrievalCandidate, RetrievalQuery, RetrievalResult
from superagent.retrieval.ports import CandidateFusion, DenseRetriever, LexicalRetriever


class HybridRetriever:
    """Main hybrid retrieval pipeline orchestrating dense, lexical, fusion, and reranking stages."""

    def __init__(
        self,
        embedding_provider: EmbeddingProvider,
        dense_retriever: DenseRetriever,
        lexical_retriever: LexicalRetriever,
        fusion: CandidateFusion | None = None,
        reranker_provider: RerankerProvider | None = None,
    ) -> None:
        self.embedding_provider = embedding_provider
        self.dense_retriever = dense_retriever
        self.lexical_retriever = lexical_retriever
        self.fusion = fusion or ReciprocalRankFusion()
        self.reranker_provider = reranker_provider

    def retrieve(self, query: RetrievalQuery) -> RetrievalResult:
        if not query.text or not query.text.strip():
            raise ValidationError("Retrieval query text cannot be empty or blank")

        start_time = time.perf_counter()

        # Step 1: Embed query text
        embed_response = self.embedding_provider.embed(EmbeddingRequest(texts=[query.text]))
        if not embed_response.embeddings or not embed_response.embeddings[0]:
            raise ValidationError("Embedding provider returned empty query vector")

        query_vector = embed_response.embeddings[0]

        # Step 2: Retrieve dense vector candidates
        dense_candidates = self.dense_retriever.retrieve_dense(
            query_vector=query_vector,
            top_k=query.candidate_k,
            filters=query.filters,
        )

        # Step 3: Retrieve lexical FTS5 candidates
        lexical_candidates = self.lexical_retriever.retrieve_lexical(
            query_text=query.text,
            top_k=query.candidate_k,
            filters=query.filters,
        )

        # Step 4: Merge candidate streams via RRF fusion
        fused_candidates = self.fusion.fuse_candidates(
            dense_candidates=dense_candidates,
            lexical_candidates=lexical_candidates,
            top_k=query.candidate_k,
        )

        # Step 5: Optional reranking
        should_rerank = False
        if query.rerank_config is not None:
            should_rerank = query.rerank_config.enabled
        elif self.reranker_provider is not None:
            should_rerank = True

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
                rerank_req = RerankRequest(
                    query=query.text,
                    candidates=[c.content for c in to_rerank],
                )
                rerank_res = self.reranker_provider.rerank(rerank_req)

                reranked_candidates: list[RetrievalCandidate] = []
                for item in rerank_res.ranked_items:
                    idx = item.get("index")
                    score = item.get("score", 0.0)
                    if idx is not None and 0 <= idx < len(to_rerank):
                        cand = to_rerank[idx]
                        updated_cand = RetrievalCandidate(
                            chunk_id=cand.chunk_id,
                            document_id=cand.document_id,
                            version_id=cand.version_id,
                            source_id=cand.source_id,
                            content=cand.content,
                            retrieval_method=cand.retrieval_method,
                            retrieval_score=score,
                            dense_score=cand.dense_score,
                            lexical_score=cand.lexical_score,
                            fused_score=cand.fused_score,
                            reranker_score=score,
                            chunk_index=cand.chunk_index,
                            metadata=cand.metadata,
                            provenance=cand.provenance,
                        )
                        reranked_candidates.append(updated_cand)

                # Append any candidates not returned in ranked_items
                seen_chunk_ids = {c.chunk_id for c in reranked_candidates}
                for cand in to_rerank:
                    if cand.chunk_id not in seen_chunk_ids:
                        reranked_candidates.append(cand)

                reranked_candidates.sort(key=lambda c: (-c.retrieval_score, c.chunk_id))
                candidates = reranked_candidates + remainder
                reranked = True

            except ProviderError:
                # If explicitly configured or provider failed, fallback to fused order
                candidates = fused_candidates

        final_candidates = candidates[: query.top_k]
        duration_ms = (time.perf_counter() - start_time) * 1000.0

        return RetrievalResult(
            query=query.text,
            candidates=final_candidates,
            total_candidates=len(final_candidates),
            dense_count=len(dense_candidates),
            lexical_count=len(lexical_candidates),
            fused_count=len(fused_candidates),
            reranked=reranked,
            duration_ms=round(duration_ms, 2),
        )
