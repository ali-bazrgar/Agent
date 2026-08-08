from __future__ import annotations

import json
from datetime import datetime, timezone

from superagent.database.config import DatabaseConfig
from superagent.database.engine import DatabaseEngine
from superagent.database.repositories.sqlite_document_version_repository import SqliteDocumentVersionRepository
from superagent.database.repositories.sqlite_embedding_repository import SqliteEmbeddingRepository
from superagent.database.repositories.sqlite_knowledge_repository import SqliteKnowledgeRepository
from superagent.database.repositories.sqlite_source_repository import SqliteSourceRepository
from superagent.database.repositories.sqlite_tag_repository import SqliteTagRepository
from superagent.models.domain import (
    DocumentVersion,
    EmbeddingRecord,
    KnowledgeItem,
    Source,
    Tag,
)


def test_sqlite_source_repository_round_trip(tmp_path) -> None:
    db_file = tmp_path / "test_sources.db"
    engine = DatabaseEngine(DatabaseConfig(path=db_file))
    engine.ensure_ready()

    repo = SqliteSourceRepository(engine)

    source = Source(
        source_id="src-1",
        source_type="file",
        uri="/tmp/test.txt",
        locator="line:1",
        title="Test Source",
        content_hash="hash123",
        metadata={"author": "alice"},
        provenance={"ip": "127.0.0.1"},
    )

    created = repo.create_source(source)
    assert created.source_id == "src-1"

    fetched = repo.get_source("src-1")
    assert fetched is not None
    assert fetched.title == "Test Source"
    assert fetched.content_hash == "hash123"
    assert fetched.metadata["author"] == "alice"

    by_hash = repo.get_source_by_content_hash("hash123")
    assert by_hash is not None
    assert by_hash.source_id == "src-1"

    sources = repo.list_sources()
    assert len(sources) == 1
    assert sources[0].source_id == "src-1"


def test_sqlite_document_version_repository_round_trip(tmp_path) -> None:
    db_file = tmp_path / "test_versions.db"
    engine = DatabaseEngine(DatabaseConfig(path=db_file))
    engine.ensure_ready()

    repo = SqliteDocumentVersionRepository(engine)

    version = DocumentVersion(
        version_id="ver-1",
        document_id="doc-1",
        title="Doc V1",
        content="Hello world v1",
        content_hash="hash_v1",
        content_type="text/plain",
        status="active",
        metadata={"rev": 1},
    )

    created = repo.create_version(version)
    assert created.version_id == "ver-1"

    fetched = repo.get_version("ver-1")
    assert fetched is not None
    assert fetched.title == "Doc V1"
    assert fetched.content == "Hello world v1"

    versions = repo.list_versions_for_document("doc-1")
    assert len(versions) == 1
    assert versions[0].version_id == "ver-1"


def test_sqlite_embedding_repository_round_trip(tmp_path) -> None:
    db_file = tmp_path / "test_embeddings.db"
    engine = DatabaseEngine(DatabaseConfig(path=db_file))
    engine.ensure_ready()

    repo = SqliteEmbeddingRepository(engine)

    record = EmbeddingRecord(
        embedding_id="emb-1",
        chunk_id="chk-1",
        document_id="doc-1",
        version_id="ver-1",
        model_id="test-model",
        dimension=3,
        vector_json=json.dumps([0.1, 0.2, 0.3]),
        content_hash="chash123",
        metadata={"idx": 0},
    )

    created = repo.create_embedding(record)
    assert created.embedding_id == "emb-1"

    fetched = repo.get_embedding("emb-1")
    assert fetched is not None
    assert fetched.dimension == 3
    assert json.loads(fetched.vector_json) == [0.1, 0.2, 0.3]

    for_chunk = repo.list_embeddings_for_chunk("chk-1")
    assert len(for_chunk) == 1
    assert for_chunk[0].embedding_id == "emb-1"


def test_sqlite_knowledge_repository_round_trip(tmp_path) -> None:
    db_file = tmp_path / "test_knowledge.db"
    engine = DatabaseEngine(DatabaseConfig(path=db_file))
    engine.ensure_ready()

    repo = SqliteKnowledgeRepository(engine)

    item = KnowledgeItem(
        knowledge_id="kno-1",
        kind="document",
        title="Knowledge 1",
        content="Important fact",
        content_hash="khash123",
        source_id="src-1",
        document_id="doc-1",
        version_id="ver-1",
        metadata={"topic": "ai"},
    )

    created = repo.create_knowledge(item)
    assert created.knowledge_id == "kno-1"

    fetched = repo.get_knowledge("kno-1")
    assert fetched is not None
    assert fetched.title == "Knowledge 1"
    assert fetched.content == "Important fact"

    items = repo.list_knowledge()
    assert len(items) == 1
    assert items[0].knowledge_id == "kno-1"


def test_sqlite_tag_repository_round_trip(tmp_path) -> None:
    db_file = tmp_path / "test_tags.db"
    engine = DatabaseEngine(DatabaseConfig(path=db_file))
    engine.ensure_ready()

    repo = SqliteTagRepository(engine)

    tag = Tag(
        tag_id="tag-1",
        resource_type="document",
        resource_id="doc-1",
        name="category",
        value="research",
    )

    created = repo.add_tag(tag)
    assert created.tag_id == "tag-1"

    tags = repo.list_tags("document", "doc-1")
    assert len(tags) == 1
    assert tags[0].name == "category"
    assert tags[0].value == "research"
