from __future__ import annotations

import pytest

from superagent.core.errors import ProviderError, ValidationError
from superagent.database.config import DatabaseConfig
from superagent.database.engine import DatabaseEngine
from superagent.database.repositories.sqlite_chunk_repository import SqliteChunkRepository
from superagent.database.repositories.sqlite_document_repository import SqliteDocumentRepository
from superagent.database.repositories.sqlite_document_version_repository import SqliteDocumentVersionRepository
from superagent.database.repositories.sqlite_embedding_repository import SqliteEmbeddingRepository
from superagent.database.repositories.sqlite_knowledge_repository import SqliteKnowledgeRepository
from superagent.database.repositories.sqlite_source_repository import SqliteSourceRepository
from superagent.database.repositories.sqlite_tag_repository import SqliteTagRepository
from superagent.knowledge.ingest.pipeline import (
    DocumentIngestionPipeline,
    IngestionRequest,
)
from superagent.providers.contracts import EmbeddingProvider, EmbeddingRequest, EmbeddingResponse


class FakeEmbeddingProvider(EmbeddingProvider):
    def __init__(self, should_fail: bool = False) -> None:
        self.should_fail = should_fail
        self.call_count = 0

    def embed(self, request: EmbeddingRequest) -> EmbeddingResponse:
        self.call_count += 1
        if self.should_fail:
            raise ProviderError("Embedding model offline", provider_name="fake_embedding")
        embeddings = [[0.1, 0.2, 0.3] for _ in request.texts]
        return EmbeddingResponse(embeddings=embeddings, provider_name="fake_embedding")

    def check_health(self):
        from superagent.providers.contracts import ProviderHealth, ProviderHealthStatus

        return ProviderHealth(
            name="fake_embedding",
            status=ProviderHealthStatus.HEALTHY if not self.should_fail else ProviderHealthStatus.UNAVAILABLE,
            message="ok",
        )

    def capabilities(self):
        from superagent.providers.contracts import ProviderCapabilities

        return ProviderCapabilities(embedding=True, batch_embedding=True)


def test_ingestion_pipeline_end_to_end(tmp_path) -> None:
    db_file = tmp_path / "test_ingest.db"
    engine = DatabaseEngine(DatabaseConfig(path=db_file))
    engine.ensure_ready()

    source_repo = SqliteSourceRepository(engine)
    doc_repo = SqliteDocumentRepository(engine)
    version_repo = SqliteDocumentVersionRepository(engine)
    chunk_repo = SqliteChunkRepository(engine)
    emb_repo = SqliteEmbeddingRepository(engine)
    knowledge_repo = SqliteKnowledgeRepository(engine)
    tag_repo = SqliteTagRepository(engine)
    emb_provider = FakeEmbeddingProvider()

    pipeline = DocumentIngestionPipeline(
        source_repository=source_repo,
        document_repository=doc_repo,
        document_version_repository=version_repo,
        chunk_repository=chunk_repo,
        embedding_repository=emb_repo,
        knowledge_repository=knowledge_repo,
        tag_repository=tag_repo,
        embedding_provider=emb_provider,
        database_engine=engine,
    )

    req = IngestionRequest(
        title="Architecture Doc",
        content="This is the full text of the architecture document. It has enough words to test.",
        source_type="file",
        uri="/docs/arch.md",
    )

    result = pipeline.ingest(req)

    assert result.is_duplicate is False
    assert result.source.source_id is not None
    assert result.document.document_id is not None
    assert result.version.version_id is not None
    assert len(result.chunks) > 0
    assert len(result.embeddings) == len(result.chunks)

    # Test duplicate ingestion
    dup_result = pipeline.ingest(req)
    assert dup_result.is_duplicate is True
    assert dup_result.document.document_id == result.document.document_id


def test_ingestion_pipeline_validation_errors(tmp_path) -> None:
    db_file = tmp_path / "test_val.db"
    engine = DatabaseEngine(DatabaseConfig(path=db_file))
    engine.ensure_ready()

    pipeline = DocumentIngestionPipeline(
        source_repository=SqliteSourceRepository(engine),
        document_repository=SqliteDocumentRepository(engine),
        document_version_repository=SqliteDocumentVersionRepository(engine),
        chunk_repository=SqliteChunkRepository(engine),
        embedding_repository=SqliteEmbeddingRepository(engine),
        knowledge_repository=SqliteKnowledgeRepository(engine),
        tag_repository=SqliteTagRepository(engine),
        embedding_provider=FakeEmbeddingProvider(),
    )

    with pytest.raises(ValidationError):
        pipeline.ingest(IngestionRequest(title="", content="valid content"))

    with pytest.raises(ValidationError):
        pipeline.ingest(IngestionRequest(title="Valid title", content="   "))


def test_ingestion_pipeline_handles_embedding_failure(tmp_path) -> None:
    db_file = tmp_path / "test_fail.db"
    engine = DatabaseEngine(DatabaseConfig(path=db_file))
    engine.ensure_ready()

    failing_provider = FakeEmbeddingProvider(should_fail=True)
    pipeline = DocumentIngestionPipeline(
        source_repository=SqliteSourceRepository(engine),
        document_repository=SqliteDocumentRepository(engine),
        document_version_repository=SqliteDocumentVersionRepository(engine),
        chunk_repository=SqliteChunkRepository(engine),
        embedding_repository=SqliteEmbeddingRepository(engine),
        knowledge_repository=SqliteKnowledgeRepository(engine),
        tag_repository=SqliteTagRepository(engine),
        embedding_provider=failing_provider,
    )

    with pytest.raises(ProviderError):
        pipeline.ingest(IngestionRequest(title="Test", content="Some text"))
