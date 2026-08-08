from __future__ import annotations

from typing import Sequence

from superagent.core.errors import PersistenceError
from superagent.database.engine import DatabaseEngine
from superagent.models.domain import Document
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
                        source_id,
                        source.source_type,
                        source.uri,
                        source.locator,
                        source.title or document.title,
                        source.content_hash or document.content_hash,
                        self.engine.to_json(source.metadata),
                        self.engine.to_json(source.provenance),
                        source.created_at.isoformat(),
                        source.updated_at.isoformat(),
                    ),
                )
                connection.execute(
                    """
                    INSERT INTO documents (id, title, source_type, source_uri, content_hash, metadata_json, created_at, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        document.document_id,
                        document.title,
                        source.source_type,
                        source.uri,
                        document.content_hash,
                        self.engine.to_json(document.metadata),
                        document.created_at.isoformat(),
                        document.updated_at.isoformat(),
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
                        document.document_id,
                        source_id,
                        document.title,
                        document.document_type,
                        document.content_type,
                        document.content_hash,
                        document.status,
                        document.version,
                        self.engine.to_json(document.metadata),
                        document.created_at.isoformat(),
                        document.updated_at.isoformat(),
                    ),
                )
                connection.commit()
        except Exception as exc:
            raise PersistenceError(f"failed to create document: {exc}") from exc
        return document

    def get_document(self, document_id: str) -> Document | None:
        with self.engine.connect() as connection:
            row = connection.execute("SELECT * FROM documents WHERE id = ?", (document_id,)).fetchone()
        return self._from_row(row) if row is not None else None

    def list_documents(self) -> Sequence[Document]:
        with self.engine.connect() as connection:
            rows = connection.execute("SELECT * FROM documents ORDER BY created_at").fetchall()
        return [self._from_row(row) for row in rows]

    def delete_document(self, document_id: str) -> bool:
        try:
            with self.engine.connect() as connection:
                row = connection.execute(
                    "SELECT source_id FROM knowledge_documents WHERE document_id = ?",
                    (document_id,),
                ).fetchone()
                if row is None:
                    exists = connection.execute("SELECT 1 FROM documents WHERE id = ?", (document_id,)).fetchone()
                    if exists is None:
                        return False
                    connection.execute("DELETE FROM documents WHERE id = ?", (document_id,))
                    connection.commit()
                    return True

                source_id = row["source_id"]
                chunk_ids = [item[0] for item in connection.execute(
                    "SELECT chunk_id FROM knowledge_chunks WHERE document_id = ?", (document_id,)
                ).fetchall()]
                if chunk_ids:
                    placeholders = ",".join("?" for _ in chunk_ids)
                    connection.execute(f"DELETE FROM chunk_search_fts WHERE chunk_id IN ({placeholders})", chunk_ids)
                    connection.execute(f"DELETE FROM lexical_index_entries WHERE chunk_id IN ({placeholders})", chunk_ids)
                    connection.execute(f"DELETE FROM embedding_records WHERE chunk_id IN ({placeholders})", chunk_ids)
                connection.execute("DELETE FROM embedding_records WHERE document_id = ?", (document_id,))
                connection.execute("DELETE FROM knowledge_items WHERE document_id = ?", (document_id,))
                connection.execute("DELETE FROM tags WHERE resource_id = ?", (document_id,))
                connection.execute("DELETE FROM document_versions WHERE document_id = ?", (document_id,))
                connection.execute("DELETE FROM knowledge_chunks WHERE document_id = ?", (document_id,))
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

    def _from_row(self, row: object) -> Document:
        from datetime import datetime

        return Document(
            document_id=row["id"],
            title=row["title"],
            source={
                "source_id": row["id"],
                "source_type": row["source_type"],
                "uri": row["source_uri"],
            },
            content_hash=row["content_hash"],
            metadata=self.engine.from_json(row["metadata_json"]) or {},
            created_at=datetime.fromisoformat(row["created_at"]),
            updated_at=datetime.fromisoformat(row["updated_at"]),
        )
