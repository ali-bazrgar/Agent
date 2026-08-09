from __future__ import annotations

from superagent.providers.contracts import EmbeddingResponse
from superagent.retrieval.models import RetrievalCandidate, RetrievalQuery
from superagent.retrieval.pipeline import HybridRetriever
from superagent.retrieval.ports import CandidateFusion, DenseRetriever, LexicalRetriever


class FakeEmbedding:
    def embed(self, request):
        return EmbeddingResponse(embeddings=[[1.0, 0.0]])


class FakeDense(DenseRetriever):
    def retrieve_dense(self, query_vector, top_k, filters=None):
        return [
            RetrievalCandidate(chunk_id="1", document_id="d1", content="a" * 40),
            RetrievalCandidate(chunk_id="2", document_id="d2", content="b" * 40),
        ][:top_k]


class FakeLexical(LexicalRetriever):
    def retrieve_lexical(self, query_text, top_k, filters=None):
        return []


class FakeFusion(CandidateFusion):
    def fuse_candidates(self, dense_candidates, lexical_candidates, top_k):
        return list(dense_candidates)[:top_k]


def test_retrieval_respects_token_budget():
    retriever = HybridRetriever(FakeEmbedding(), FakeDense(), FakeLexical(), fusion=FakeFusion())
    result = retriever.retrieve(RetrievalQuery(text="query", top_k=2, candidate_k=2, token_budget=18))

    assert len(result.candidates) == 1
    assert result.estimated_tokens <= 18
    assert result.token_budget == 18
