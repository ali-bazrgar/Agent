from datetime import datetime, timezone

from superagent.database.config import DatabaseConfig
from superagent.database.engine import DatabaseEngine
from superagent.database.repositories.sqlite_chunk_repository import SqliteChunkRepository
from superagent.database.repositories.sqlite_document_repository import SqliteDocumentRepository
from superagent.database.repositories.sqlite_document_version_repository import SqliteDocumentVersionRepository
from superagent.database.repositories.sqlite_embedding_repository import SqliteEmbeddingRepository
from superagent.database.repositories.sqlite_knowledge_repository import SqliteKnowledgeRepository
from superagent.database.repositories.sqlite_source_repository import SqliteSourceRepository
from superagent.models.domain import Document, DocumentChunk, DocumentVersion, EmbeddingRecord, KnowledgeItem, Source


def test_document_round_trip_includes_real_source_and_chunks(tmp_path):
    engine = DatabaseEngine(DatabaseConfig(path=tmp_path / "roundtrip.db"))
    engine.ensure_ready()
    source = Source(source_id="src-1", source_type="file", uri="/tmp/a.md", title="A")
    document = Document(document_id="doc-1", title="A", source=source, source_id="src-1", document_type="markdown", content_type="text/markdown")
    SqliteDocumentRepository(engine).create_document(document)
    SqliteDocumentVersionRepository(engine).create_version(DocumentVersion(version_id="ver-1", document_id="doc-1", title="A", content="# A"))
    SqliteChunkRepository(engine).create_chunk(DocumentChunk(chunk_id="chunk-1", document_id="doc-1", version_id="ver-1", content="hello", chunk_index=0, token_count=1, character_count=5))

    loaded = SqliteDocumentRepository(engine).get_document("doc-1")

    assert loaded is not None
    assert loaded.source.source_id == "src-1"
    assert loaded.source.uri == "/tmp/a.md"
    assert loaded.document_type == "markdown"
    assert len(loaded.chunks) == 1
    assert loaded.chunks[0].chunk_id == "chunk-1"


def test_document_delete_cleans_legacy_and_knowledge_indexes(tmp_path):
    engine = DatabaseEngine(DatabaseConfig(path=tmp_path / "delete.db"))
    engine.ensure_ready()
    source = Source(source_id="src-1", source_type="file", uri="/tmp/a.md", title="A")
    SqliteDocumentRepository(engine).create_document(Document(document_id="doc-1", title="A", source=source, source_id="src-1"))
    SqliteDocumentVersionRepository(engine).create_version(DocumentVersion(version_id="ver-1", document_id="doc-1", content="hello"))
    SqliteChunkRepository(engine).create_chunk(DocumentChunk(chunk_id="chunk-1", document_id="doc-1", version_id="ver-1", content="hello", chunk_index=0))
    SqliteKnowledgeRepository(engine).create_knowledge(KnowledgeItem(knowledge_id="knowledge-1", kind="fact", content="hello", source_id="src-1", document_id="doc-1", version_id="ver-1", chunk_id="chunk-1"))
    SqliteEmbeddingRepository(engine).create_embedding(EmbeddingRecord(embedding_id="emb-1", chunk_id="chunk-1", document_id="doc-1", version_id="ver-1", model_id="test", dimension=2, vector_json="[0.1,0.2]"))

    assert SqliteDocumentRepository(engine).delete_document("doc-1") is True

    with engine.connect() as connection:
        for table in ("documents", "knowledge_documents", "knowledge_chunks", "document_chunks", "knowledge_items", "embedding_records", "document_versions"):
            assert connection.execute(f"SELECT COUNT(*) FROM {table} WHERE " + ("id = ?" if table in {"documents", "document_chunks"} else "document_id = ?"), ("doc-1",)).fetchone()[0] == 0 if table != "embedding_records" else connection.execute("SELECT COUNT(*) FROM embedding_records WHERE document_id = ?", ("doc-1",)).fetchone()[0] == 0
