from __future__ import annotations

import json
import pytest

from superagent.core.errors import ValidationError
from superagent.database.config import DatabaseConfig
from superagent.database.engine import DatabaseEngine
from superagent.models.domain import DocumentChunk, EmbeddingRecord
from superagent.database.repositories.sqlite_chunk_repository import SqliteChunkRepository
from superagent.database.repositories.sqlite_embedding_repository import SqliteEmbeddingRepository
from superagent.retrieval.dense import SqliteDenseRetriever


def test_vector_retrieval_empty_db(tmp_path) -> None:
    db_path = tmp_path / "test_dense.db"
    engine = DatabaseEngine(DatabaseConfig(path=db_path))
    engine.ensure_ready()

    retriever = SqliteDenseRetriever(engine)
    candidates = retriever.retrieve_dense(query_vector=[0.1, 0.2, 0.3], top_k=5)
    assert candidates == []


def test_vector_retrieval_empty_query_vector(tmp_path) -> None:
    db_path = tmp_path / "test_dense.db"
    engine = DatabaseEngine(DatabaseConfig(path=db_path))
    engine.ensure_ready()

    retriever = SqliteDenseRetriever(engine)
    with pytest.raises(ValidationError, match="query_vector cannot be empty"):
        retriever.retrieve_dense(query_vector=[], top_k=5)


def test_vector_retrieval_cosine_similarity_and_ranking(tmp_path) -> None:
    db_path = tmp_path / "test_dense.db"
    engine = DatabaseEngine(DatabaseConfig(path=db_path))
    engine.ensure_ready()

    chunk_repo = SqliteChunkRepository(engine)
    emb_repo = SqliteEmbeddingRepository(engine)

    # Insert two chunks and their embeddings
    chunk1 = DocumentChunk(chunk_id="chk-1", document_id="doc-1", content="Python AI agent framework", chunk_index=0)
    chunk2 = DocumentChunk(chunk_id="chk-2", document_id="doc-1", content="Cooking recipe for pasta", chunk_index=1)
    chunk_repo.create_chunk(chunk1)
    chunk_repo.create_chunk(chunk2)

    # Vector 1 is aligned with query [1.0, 0.0]
    emb1 = EmbeddingRecord(
        embedding_id="emb-1",
        chunk_id="chk-1",
        document_id="doc-1",
        model_id="test-emb",
        dimension=2,
        vector_json=json.dumps([1.0, 0.0]),
    )
    # Vector 2 is orthogonal/different [0.0, 1.0]
    emb2 = EmbeddingRecord(
        embedding_id="emb-2",
        chunk_id="chk-2",
        document_id="doc-1",
        model_id="test-emb",
        dimension=2,
        vector_json=json.dumps([0.0, 1.0]),
    )
    emb_repo.create_embedding(emb1)
    emb_repo.create_embedding(emb2)

    retriever = SqliteDenseRetriever(engine)
    candidates = retriever.retrieve_dense(query_vector=[1.0, 0.0], top_k=10)

    assert len(candidates) == 2
    assert candidates[0].chunk_id == "chk-1"
    assert pytest.approx(candidates[0].dense_score, 0.001) == 1.0
    assert candidates[1].chunk_id == "chk-2"
    assert pytest.approx(candidates[1].dense_score, 0.001) == 0.0


def test_vector_retrieval_dimension_mismatch(tmp_path) -> None:
    db_path = tmp_path / "test_dense.db"
    engine = DatabaseEngine(DatabaseConfig(path=db_path))
    engine.ensure_ready()

    chunk_repo = SqliteChunkRepository(engine)
    emb_repo = SqliteEmbeddingRepository(engine)

    chunk1 = DocumentChunk(chunk_id="chk-1", document_id="doc-1", content="Test content", chunk_index=0)
    chunk_repo.create_chunk(chunk1)

    emb1 = EmbeddingRecord(
        embedding_id="emb-1",
        chunk_id="chk-1",
        document_id="doc-1",
        model_id="test-emb",
        dimension=3,
        vector_json=json.dumps([1.0, 0.0, 0.5]),
    )
    emb_repo.create_embedding(emb1)

    retriever = SqliteDenseRetriever(engine)
    with pytest.raises(ValidationError, match="dimension"):
        retriever.retrieve_dense(query_vector=[1.0, 0.0], top_k=5)
