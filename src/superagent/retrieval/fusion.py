from __future__ import annotations

from typing import Sequence

from superagent.retrieval.models import RetrievalCandidate
from superagent.retrieval.ports import CandidateFusion


class ReciprocalRankFusion(CandidateFusion):
    """Reciprocal Rank Fusion (RRF) implementation for candidate merging."""

    def __init__(self, k: int = 60) -> None:
        self.k = k

    def fuse_candidates(
        self,
        dense_candidates: Sequence[RetrievalCandidate],
        lexical_candidates: Sequence[RetrievalCandidate],
        top_k: int,
    ) -> list[RetrievalCandidate]:
        if top_k <= 0:
            return []

        scores: dict[str, float] = {}
        candidate_map: dict[str, RetrievalCandidate] = {}
        dense_seen: set[str] = set()
        lexical_seen: set[str] = set()

        for index, candidate in enumerate(dense_candidates):
            cid = candidate.chunk_id
            rank = index + 1
            rrf_val = 1.0 / (self.k + rank)
            scores[cid] = scores.get(cid, 0.0) + rrf_val
            candidate_map[cid] = candidate
            dense_seen.add(cid)

        for index, candidate in enumerate(lexical_candidates):
            cid = candidate.chunk_id
            rank = index + 1
            rrf_val = 1.0 / (self.k + rank)
            scores[cid] = scores.get(cid, 0.0) + rrf_val
            lexical_seen.add(cid)

            if cid not in candidate_map:
                candidate_map[cid] = candidate
            else:
                # Merge scores and metadata
                existing = candidate_map[cid]
                existing.lexical_score = candidate.lexical_score

        fused_candidates: list[RetrievalCandidate] = []
        for cid, score in scores.items():
            base = candidate_map[cid]
            in_dense = cid in dense_seen
            in_lexical = cid in lexical_seen

            if in_dense and in_lexical:
                method = "hybrid"
            elif in_dense:
                method = "dense"
            else:
                method = "lexical"

            fused_candidate = RetrievalCandidate(
                chunk_id=base.chunk_id,
                document_id=base.document_id,
                version_id=base.version_id,
                source_id=base.source_id,
                content=base.content,
                retrieval_method=method,
                retrieval_score=score,
                dense_score=base.dense_score,
                lexical_score=base.lexical_score,
                fused_score=score,
                reranker_score=base.reranker_score,
                chunk_index=base.chunk_index,
                metadata=dict(base.metadata),
                provenance=dict(base.provenance),
            )
            fused_candidates.append(fused_candidate)

        # Deterministic ordering: fused_score desc, chunk_id asc
        fused_candidates.sort(key=lambda c: (-c.fused_score if c.fused_score is not None else 0.0, c.chunk_id))
        return fused_candidates[:top_k]
