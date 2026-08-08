from __future__ import annotations

from superagent.database.config import DatabaseConfig
from superagent.database.engine import DatabaseEngine
from superagent.models.domain import DocumentChunk
from superagent.database.repositories.sqlite_chunk_repository import SqliteChunkRepository
from superagent.retrieval.lexical import SqliteLexicalRetriever


def test_lexical_retrieval_empty_db(tmp_path) -> None:
    db_path = tmp_path / "test_lexical.db"
    engine = DatabaseEngine(DatabaseConfig(path=db_path))
    engine.ensure_ready()

    retriever = SqliteLexicalRetriever(engine)
    candidates = retriever.retrieve_lexical(query_text="python architecture", top_k=5)
    assert candidates == []


def test_lexical_retrieval_blank_query(tmp_path) -> None:
    db_path = tmp_path / "test_lexical.db"
    engine = DatabaseEngine(DatabaseConfig(path=db_path))
    engine.ensure_ready()

    retriever = SqliteLexicalRetriever(engine)
    assert retriever.retrieve_lexical(query_text="   ", top_k=5) == []


def test_lexical_retrieval_fts_matching(tmp_path) -> None:
    db_path = tmp_path / "test_lexical.db"
    engine = DatabaseEngine(DatabaseConfig(path=db_path))
    engine.ensure_ready()

    chunk_repo = SqliteChunkRepository(engine)

    chunk1 = DocumentChunk(chunk_id="chk-1", document_id="doc-1", content="Hexagonal architecture in Python applications.", chunk_index=0)
    chunk2 = DocumentChunk(chunk_id="chk-2", document_id="doc-1", content="Baking delicious sourdough bread at home.", chunk_index=1)
    chunk_repo.create_chunk(chunk1)
    chunk_repo.create_chunk(chunk2)

    retriever = SqliteLexicalRetriever(engine)
    candidates = retriever.retrieve_lexical(query_text="Python architecture", top_k=10)

    assert len(candidates) >= 1
    assert candidates[0].chunk_id == "chk-1"
    assert candidates[0].lexical_score > 0.0
    assert "Hexagonal architecture" in candidates[0].content


def test_lexical_retrieval_query_sanitization(tmp_path) -> None:
    db_path = tmp_path / "test_lexical.db"
    engine = DatabaseEngine(DatabaseConfig(path=db_path))
    engine.ensure_ready()

    chunk_repo = SqliteChunkRepository(engine)
    chunk1 = DocumentChunk(chunk_id="chk-1", document_id="doc-1", content="Clean architecture and ports & adapters.", chunk_index=0)
    chunk_repo.create_chunk(chunk1)

    retriever = SqliteLexicalRetriever(engine)
    # Query with special characters/punctuation
    candidates = retriever.retrieve_lexical(query_text='SELECT * FROM "clean" AND (architecture)!', top_k=5)
    assert len(candidates) == 1
    assert candidates[0].chunk_id == "chk-1"
