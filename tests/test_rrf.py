from __future__ import annotations

from superagent.retrieval.fusion import ReciprocalRankFusion
from superagent.retrieval.models import RetrievalCandidate


def test_rrf_fusion_merging_and_scoring() -> None:
    c1 = RetrievalCandidate(chunk_id="chk-1", document_id="doc-1", content="Chunk 1", retrieval_method="dense", dense_score=0.9)
    c2 = RetrievalCandidate(chunk_id="chk-2", document_id="doc-1", content="Chunk 2", retrieval_method="dense", dense_score=0.8)
    c3 = RetrievalCandidate(chunk_id="chk-3", document_id="doc-1", content="Chunk 3", retrieval_method="lexical", lexical_score=1.5)

    dense_candidates = [c1, c2]
    # c2 is first in lexical, c3 is second
    c2_lex = RetrievalCandidate(chunk_id="chk-2", document_id="doc-1", content="Chunk 2", retrieval_method="lexical", lexical_score=2.0)
    lexical_candidates = [c2_lex, c3]

    fusion = ReciprocalRankFusion(k=60)
    fused = fusion.fuse_candidates(dense_candidates, lexical_candidates, top_k=10)

    assert len(fused) == 3

    # chk-2 is rank 2 in dense (1/(60+2)) and rank 1 in lexical (1/(60+1))
    # score = 1/62 + 1/61 = ~0.016129 + ~0.016393 = ~0.032522
    assert fused[0].chunk_id == "chk-2"
    assert fused[0].retrieval_method == "hybrid"
    assert fused[0].fused_score > fused[1].fused_score

    # Check method assignments for single-source candidates
    chunk_map = {c.chunk_id: c for c in fused}
    assert chunk_map["chk-1"].retrieval_method == "dense"
    assert chunk_map["chk-3"].retrieval_method == "lexical"


def test_rrf_top_k_cutoff() -> None:
    c1 = RetrievalCandidate(chunk_id="chk-1", document_id="doc-1", content="Chunk 1", retrieval_method="dense", dense_score=0.9)
    c2 = RetrievalCandidate(chunk_id="chk-2", document_id="doc-1", content="Chunk 2", retrieval_method="dense", dense_score=0.8)

    fusion = ReciprocalRankFusion(k=60)
    fused = fusion.fuse_candidates([c1, c2], [], top_k=1)
    assert len(fused) == 1
    assert fused[0].chunk_id == "chk-1"
