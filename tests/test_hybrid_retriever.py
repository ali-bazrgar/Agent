from __future__ import annotations

import json
import pytest

from superagent.core.errors import ValidationError
from superagent.database.config import DatabaseConfig
from superagent.database.engine import DatabaseEngine
from superagent.models.domain import DocumentChunk, EmbeddingRecord
from superagent.providers.contracts import (
    EmbeddingProvider,
    EmbeddingRequest,
    EmbeddingResponse,
    ProviderCapabilities,
    ProviderHealth,
    ProviderHealthStatus,
    RerankerProvider,
    RerankRequest,
    RerankResponse,
)
from superagent.database.repositories.sqlite_chunk_repository import SqliteChunkRepository
from superagent.database.repositories.sqlite_embedding_repository import SqliteEmbeddingRepository
from superagent.retrieval.dense import SqliteDenseRetriever
from superagent.retrieval.fusion import ReciprocalRankFusion
from superagent.retrieval.lexical import SqliteLexicalRetriever
from superagent.retrieval.models import RerankConfig, RetrievalQuery
from superagent.retrieval.pipeline import HybridRetriever


class MockEmbeddingProvider(EmbeddingProvider):
    def embed(self, request: EmbeddingRequest) -> EmbeddingResponse:
        return EmbeddingResponse(embeddings=[[1.0, 0.0] for _ in request.texts], provider_name="mock")

    def check_health(self) -> ProviderHealth:
        return ProviderHealth(name="mock", status=ProviderHealthStatus.HEALTHY)

    def capabilities(self) -> ProviderCapabilities:
        return ProviderCapabilities(embedding=True)


class MockRerankerProvider(RerankerProvider):
    def rerank(self, request: RerankRequest) -> RerankResponse:
        # Reverse order for test
        ranked = [
            {"index": i, "score": float(len(request.candidates) - i), "text": cand}
            for i, cand in enumerate(request.candidates)
        ]
        return RerankResponse(ranked_items=ranked, provider_name="mock")

    def check_health(self) -> ProviderHealth:
        return ProviderHealth(name="mock", status=ProviderHealthStatus.HEALTHY)

    def capabilities(self) -> ProviderCapabilities:
        return ProviderCapabilities(reranking=True)


def test_hybrid_retriever_empty_query_raises() -> None:
    embedder = MockEmbeddingProvider()
    retriever = HybridRetriever(
        embedding_provider=embedder,
        dense_retriever=None,  # type: ignore
        lexical_retriever=None,  # type: ignore
    )
    with pytest.raises(ValidationError, match="cannot be empty"):
        retriever.retrieve(RetrievalQuery(text="   "))


def test_hybrid_retriever_end_to_end(tmp_path) -> None:
    db_path = tmp_path / "test_hybrid.db"
    engine = DatabaseEngine(DatabaseConfig(path=db_path))
    engine.ensure_ready()

    chunk_repo = SqliteChunkRepository(engine)
    emb_repo = SqliteEmbeddingRepository(engine)

    chunk1 = DocumentChunk(chunk_id="chk-1", document_id="doc-1", content="Python RAG retrieval engine", chunk_index=0)
    chunk2 = DocumentChunk(chunk_id="chk-2", document_id="doc-1", content="Deep learning neural networks", chunk_index=1)
    chunk_repo.create_chunk(chunk1)
    chunk_repo.create_chunk(chunk2)

    emb1 = EmbeddingRecord(
        embedding_id="emb-1",
        chunk_id="chk-1",
        document_id="doc-1",
        model_id="mock",
        dimension=2,
        vector_json=json.dumps([1.0, 0.0]),
    )
    emb2 = EmbeddingRecord(
        embedding_id="emb-2",
        chunk_id="chk-2",
        document_id="doc-1",
        model_id="mock",
        dimension=2,
        vector_json=json.dumps([0.0, 1.0]),
    )
    emb_repo.create_embedding(emb1)
    emb_repo.create_embedding(emb2)

    embedder = MockEmbeddingProvider()
    reranker = MockRerankerProvider()
    dense_retriever = SqliteDenseRetriever(engine)
    lexical_retriever = SqliteLexicalRetriever(engine)
    fusion = ReciprocalRankFusion(k=60)

    hybrid = HybridRetriever(
        embedding_provider=embedder,
        dense_retriever=dense_retriever,
        lexical_retriever=lexical_retriever,
        fusion=fusion,
        reranker_provider=reranker,
    )

    query = RetrievalQuery(
        text="Python RAG retrieval engine",
        top_k=2,
        candidate_k=5,
        rerank_config=RerankConfig(enabled=True),
    )
    res = hybrid.retrieve(query)

    assert res.query == "Python RAG retrieval engine"
    assert res.total_candidates >= 1
    assert res.reranked is True
    assert res.duration_ms >= 0.0
    assert len(res.candidates) <= 2
