from superagent.providers.contracts import EmbeddingResponse, ProviderCapabilities, ProviderHealth, ProviderHealthStatus, RerankResponse
from superagent.retrieval.models import RetrievalCandidate, RetrievalQuery
from superagent.retrieval.pipeline import HybridRetriever


class FakeEmbeddingProvider:
    def embed(self, request):
        return EmbeddingResponse(embeddings=[[1.0, 0.0]])

    def check_health(self):
        return ProviderHealth(name="embedding", status=ProviderHealthStatus.HEALTHY)

    def capabilities(self):
        return ProviderCapabilities(embeddings=True)


class FakeRerankerProvider:
    def __init__(self):
        self.calls = 0

    def rerank(self, request):
        self.calls += 1
        return RerankResponse(ranked_items=[{"index": 1, "score": 0.95}, {"index": 0, "score": 0.10}])

    def check_health(self):
        return ProviderHealth(name="reranker", status=ProviderHealthStatus.HEALTHY)

    def capabilities(self):
        return ProviderCapabilities(reranking=True)


class FakeDense:
    def retrieve_dense(self, query_vector, top_k, filters=None):
        return [
            RetrievalCandidate(chunk_id="a", document_id="d", content="first", retrieval_score=0.9),
            RetrievalCandidate(chunk_id="b", document_id="d", content="second", retrieval_score=0.8),
        ]


class FakeLexical:
    def retrieve_lexical(self, query_text, top_k, filters=None):
        return [
            RetrievalCandidate(chunk_id="a", document_id="d", content="first", retrieval_score=0.7),
            RetrievalCandidate(chunk_id="b", document_id="d", content="second", retrieval_score=0.6),
        ]


def test_existing_hybrid_pipeline_invokes_real_reranker_and_preserves_budget():
    reranker = FakeRerankerProvider()
    retriever = HybridRetriever(
        embedding_provider=FakeEmbeddingProvider(),
        dense_retriever=FakeDense(),
        lexical_retriever=FakeLexical(),
        reranker_provider=reranker,
    )

    result = retriever.retrieve(
        RetrievalQuery(text="query", top_k=1, candidate_k=2, token_budget=10)
    )

    assert reranker.calls == 1
    assert result.reranked is True
    assert len(result.candidates) == 1
    assert result.candidates[0].chunk_id == "b"
    assert result.estimated_tokens <= 10
