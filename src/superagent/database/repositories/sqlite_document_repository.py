from __future__ import annotations

from typing import Sequence

from superagent.core.errors import PersistenceError
from superagent.database.engine import DatabaseEngine
from superagent.models.domain import Document, DocumentChunk, Source
from superagent.repositories.ports import DocumentRepository


class SqliteDocumentRepository(DocumentRepository):
    def __init__(self, engine: DatabaseEngine) -> None:
        self.engine = engine

    def create_document(self, document: Document) -> Document:
        try:
            with self.engine.connect() as connection:
                source_id = document.source_id or document.source.source_id
                source = document.source
                connection.execute(
                    """
                    INSERT OR IGNORE INTO sources (
                        source_id, source_type, uri, locator, title, content_hash,
                        metadata_json, provenance_json, created_at, updated_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        source_id, source.source_type, source.uri, source.locator,
                        source.title or document.title,
                        source.content_hash or document.content_hash,
                        self.engine.to_json(source.metadata), self.engine.to_json(source.provenance),
                        source.created_at.isoformat(), source.updated_at.isoformat(),
                    ),
                )
                connection.execute(
                    """
                    INSERT INTO documents (id, title, source_type, source_uri, content_hash, metadata_json, created_at, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        document.document_id, document.title, source.source_type, source.uri,
                        document.content_hash, self.engine.to_json(document.metadata),
                        document.created_at.isoformat(), document.updated_at.isoformat(),
                    ),
                )
                connection.execute(
                    """
                    INSERT INTO knowledge_documents (
                        document_id, source_id, title, document_type, content_type,
                        content_hash, status, version, metadata_json, created_at, updated_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        document.document_id, source_id, document.title, document.document_type,
                        document.content_type, document.content_hash, document.status, document.version,
                        self.engine.to_json(document.metadata), document.created_at.isoformat(), document.updated_at.isoformat(),
                    ),
                )
                connection.commit()
        except Exception as exc:
            raise PersistenceError(f"failed to create document: {exc}") from exc
        return document

    def get_document(self, document_id: str) -> Document | None:
        with self.engine.connect() as connection:
            row = connection.execute("SELECT * FROM documents WHERE id = ?", (document_id,)).fetchone()
            if row is None:
                return None
            return self._from_row(connection, row)

    def list_documents(self) -> Sequence[Document]:
        with self.engine.connect() as connection:
            rows = connection.execute("SELECT * FROM documents ORDER BY created_at").fetchall()
            return [self._from_row(connection, row) for row in rows]

    def delete_document(self, document_id: str) -> bool:
        try:
            with self.engine.connect() as connection:
                row = connection.execute(
                    "SELECT source_id FROM knowledge_documents WHERE document_id = ?",
                    (document_id,),
                ).fetchone()
                exists = connection.execute("SELECT 1 FROM documents WHERE id = ?", (document_id,)).fetchone()
                if exists is None and row is None:
                    return False

                source_id = row["source_id"] if row is not None else None
                knowledge_chunk_ids = [item[0] for item in connection.execute(
                    "SELECT chunk_id FROM knowledge_chunks WHERE document_id = ?", (document_id,)
                ).fetchall()]
                legacy_chunk_ids = [item[0] for item in connection.execute(
                    "SELECT id FROM document_chunks WHERE document_id = ?", (document_id,)
                ).fetchall()]
                all_chunk_ids = list(dict.fromkeys(knowledge_chunk_ids + legacy_chunk_ids))
                if all_chunk_ids:
                    placeholders = ",".join("?" for _ in all_chunk_ids)
                    connection.execute(f"DELETE FROM chunk_search_fts WHERE chunk_id IN ({placeholders})", all_chunk_ids)
                    connection.execute(f"DELETE FROM lexical_index_entries WHERE chunk_id IN ({placeholders})", all_chunk_ids)
                    connection.execute(f"DELETE FROM embedding_records WHERE chunk_id IN ({placeholders})", all_chunk_ids)

                connection.execute("DELETE FROM embedding_records WHERE document_id = ?", (document_id,))
                connection.execute("DELETE FROM knowledge_items WHERE document_id = ?", (document_id,))
                connection.execute("DELETE FROM tags WHERE resource_id = ?", (document_id,))
                connection.execute("DELETE FROM knowledge_relationships WHERE source_id = ? OR target_id = ?", (document_id, document_id))
                connection.execute("DELETE FROM document_versions WHERE document_id = ?", (document_id,))
                connection.execute("DELETE FROM knowledge_chunks WHERE document_id = ?", (document_id,))
                connection.execute("DELETE FROM document_chunks WHERE document_id = ?", (document_id,))
                connection.execute("DELETE FROM knowledge_documents WHERE document_id = ?", (document_id,))
                connection.execute("DELETE FROM documents WHERE id = ?", (document_id,))

                if source_id:
                    remaining = connection.execute(
                        "SELECT 1 FROM knowledge_documents WHERE source_id = ? LIMIT 1", (source_id,)
                    ).fetchone()
                    if remaining is None:
                        connection.execute("DELETE FROM sources WHERE source_id = ?", (source_id,))
                connection.commit()
                return True
        except Exception as exc:
            raise PersistenceError(f"failed to delete document: {exc}") from exc

    def _from_row(self, connection: object, row: object) -> Document:
        from datetime import datetime

        source_row = connection.execute(
            "SELECT * FROM sources WHERE source_id = ?", (row["source_type"] and self._source_id_for_document(connection, row["id"]),)
        ).fetchone()
        source = Source(
            source_id=source_row["source_id"] if source_row is not None else self._source_id_for_document(connection, row["id"]),
            source_type=source_row["source_type"] if source_row is not None else row["source_type"],
            uri=source_row["uri"] if source_row is not None else row["source_uri"],
            locator=source_row["locator"] if source_row is not None else None,
            title=source_row["title"] if source_row is not None else row["title"],
            content_hash=source_row["content_hash"] if source_row is not None else row["content_hash"],
            metadata=self.engine.from_json(source_row["metadata_json"]) if source_row is not None else {},
            provenance=self.engine.from_json(source_row["provenance_json"]) if source_row is not None else None,
            created_at=datetime.fromisoformat(source_row["created_at"]) if source_row is not None else datetime.fromisoformat(row["created_at"]),
            updated_at=datetime.fromisoformat(source_row["updated_at"]) if source_row is not None else datetime.fromisoformat(row["updated_at"]),
        )
        chunk_rows = connection.execute(
            "SELECT * FROM knowledge_chunks WHERE document_id = ? ORDER BY chunk_index", (row["id"],)
        ).fetchall()
        chunks: list[DocumentChunk] = []
        if chunk_rows:
            chunks = [
                DocumentChunk(
                    chunk_id=item["chunk_id"], document_id=item["document_id"], version_id=item["version_id"],
                    content=item["content"], content_hash=item["content_hash"], chunk_index=item["chunk_index"],
                    token_count=item["token_count"], character_count=item["character_count"], language=item["language"],
                    metadata=self.engine.from_json(item["metadata_json"]) or {},
                    created_at=datetime.fromisoformat(item["created_at"]),
                )
                for item in chunk_rows
            ]
        else:
            legacy_rows = connection.execute(
                "SELECT * FROM document_chunks WHERE document_id = ? ORDER BY chunk_index", (row["id"],)
            ).fetchall()
            chunks = [
                DocumentChunk(
                    chunk_id=item["id"], document_id=item["document_id"], content=item["content"],
                    chunk_index=item["chunk_index"], token_count=item["token_count"],
                    metadata=self.engine.from_json(item["metadata_json"]) or {},
                    created_at=datetime.fromisoformat(item["created_at"]),
                )
                for item in legacy_rows
            ]

        knowledge_row = connection.execute(
            "SELECT source_id, document_type, content_type, status, version, blob_uri FROM knowledge_documents WHERE document_id = ?",
            (row["id"],),
        ).fetchone()
        return Document(
            document_id=row["id"], title=row["title"], source=source,
            source_id=knowledge_row["source_id"] if knowledge_row is not None else source.source_id,
            document_type=knowledge_row["document_type"] if knowledge_row is not None else "document",
            content_type=knowledge_row["content_type"] if knowledge_row is not None else None,
            content_hash=row["content_hash"],
            status=knowledge_row["status"] if knowledge_row is not None else "active",
            version=knowledge_row["version"] if knowledge_row is not None else 1,
            blob_uri=knowledge_row["blob_uri"] if knowledge_row is not None else None,
            metadata=self.engine.from_json(row["metadata_json"]) or {},
            chunks=chunks,
            created_at=datetime.fromisoformat(row["created_at"]),
            updated_at=datetime.fromisoformat(row["updated_at"]),
        )

    @staticmethod
    def _source_id_for_document(connection: object, document_id: str) -> str:
        row = connection.execute(
            "SELECT source_id FROM knowledge_documents WHERE document_id = ?", (document_id,)
        ).fetchone()
        return row["source_id"] if row is not None else document_id
