from __future__ import annotations

import json

from superagent.database.config import DatabaseConfig
from superagent.database.engine import DatabaseEngine
from superagent.models.domain import Document, DocumentChunk, EmbeddingRecord, Source
from superagent.database.repositories.sqlite_chunk_repository import SqliteChunkRepository
from superagent.database.repositories.sqlite_document_repository import SqliteDocumentRepository
from superagent.database.repositories.sqlite_embedding_repository import SqliteEmbeddingRepository
from superagent.database.repositories.sqlite_source_repository import SqliteSourceRepository
from superagent.retrieval.dense import SqliteDenseRetriever
from superagent.retrieval.lexical import SqliteLexicalRetriever
from superagent.retrieval.models import RetrievalFilter


def test_retrieval_filters_by_source_and_document(tmp_path) -> None:
    db_path = tmp_path / "test_filters.db"
    engine = DatabaseEngine(DatabaseConfig(path=db_path))
    engine.ensure_ready()

    source_repo = SqliteSourceRepository(engine)
    doc_repo = SqliteDocumentRepository(engine)
    chunk_repo = SqliteChunkRepository(engine)
    emb_repo = SqliteEmbeddingRepository(engine)

    # Create Source 1 & Doc 1
    s1 = Source(source_id="src-1", source_type="pdf", uri="file://1.pdf", title="Source 1")
    source_repo.create_source(s1)
    d1 = Document(document_id="doc-1", title="Doc 1", source=s1, source_id="src-1", document_type="pdf")
    doc_repo.create_document(d1)
    c1 = DocumentChunk(chunk_id="chk-1", document_id="doc-1", content="Content in Document 1 PDF", chunk_index=0)
    chunk_repo.create_chunk(c1)
    e1 = EmbeddingRecord(embedding_id="emb-1", chunk_id="chk-1", document_id="doc-1", model_id="m", dimension=2, vector_json=json.dumps([1.0, 0.0]))
    emb_repo.create_embedding(e1)

    # Create Source 2 & Doc 2
    s2 = Source(source_id="src-2", source_type="web", uri="https://example.com")
    source_repo.create_source(s2)
    d2 = Document(document_id="doc-2", title="Doc 2", source=s2, source_id="src-2", document_type="web")
    doc_repo.create_document(d2)
    c2 = DocumentChunk(chunk_id="chk-2", document_id="doc-2", content="Content in Document 2 Web", chunk_index=0)
    chunk_repo.create_chunk(c2)
    e2 = EmbeddingRecord(embedding_id="emb-2", chunk_id="chk-2", document_id="doc-2", model_id="m", dimension=2, vector_json=json.dumps([1.0, 0.0]))
    emb_repo.create_embedding(e2)

    dense = SqliteDenseRetriever(engine)
    lexical = SqliteLexicalRetriever(engine)

    # Filter by source_ids=['src-1']
    f_src1 = RetrievalFilter(source_ids=["src-1"])
    dense_res = dense.retrieve_dense([1.0, 0.0], top_k=10, filters=f_src1)
    lexical_res = lexical.retrieve_lexical("Content Document", top_k=10, filters=f_src1)

    assert len(dense_res) == 1
    assert dense_res[0].chunk_id == "chk-1"

    assert len(lexical_res) == 1
    assert lexical_res[0].chunk_id == "chk-1"

    # Filter by document_ids=['doc-2']
    f_doc2 = RetrievalFilter(document_ids=["doc-2"])
    dense_res2 = dense.retrieve_dense([1.0, 0.0], top_k=10, filters=f_doc2)
    lexical_res2 = lexical.retrieve_lexical("Content Document", top_k=10, filters=f_doc2)

    assert len(dense_res2) == 1
    assert dense_res2[0].chunk_id == "chk-2"

    assert len(lexical_res2) == 1
    assert lexical_res2[0].chunk_id == "chk-2"
