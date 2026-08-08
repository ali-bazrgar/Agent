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
                connection.execute(
                    """
                    INSERT INTO documents (id, title, source_type, source_uri, content_hash, metadata_json, created_at, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        document.document_id,
                        document.title,
                        document.source.source_type,
                        document.source.uri,
                        document.content_hash,
                        self.engine.to_json(document.metadata),
                        document.created_at.isoformat(),
                        document.updated_at.isoformat(),
                    ),
                )
                source_id = document.source_id or (document.source.source_id if document.source else None)
                if source_id:
                    try:
                        connection.execute(
                            """
                            INSERT INTO knowledge_documents (document_id, source_id, title, document_type, content_type, content_hash, status, version, metadata_json, created_at, updated_at)
                            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                            """,
                            (
                                document.document_id,
                                source_id,
                                document.title,
                                document.document_type or "document",
                                document.content_type,
                                document.content_hash,
                                document.status or "active",
                                document.version or 1,
                                self.engine.to_json(document.metadata),
                                document.created_at.isoformat(),
                                document.updated_at.isoformat(),
                            ),
                        )
                    except Exception:
                        pass
                connection.commit()
        except Exception as exc:  # pragma: no cover - defensive branch
            raise PersistenceError(f"failed to create document: {exc}") from exc
        return document

    def get_document(self, document_id: str) -> Document | None:
        with self.engine.connect() as connection:
            row = connection.execute(
                "SELECT * FROM documents WHERE id = ?",
                (document_id,),
            ).fetchone()
        if row is None:
            return None
        return self._from_row(row)

    def list_documents(self) -> Sequence[Document]:
        with self.engine.connect() as connection:
            rows = connection.execute("SELECT * FROM documents ORDER BY created_at").fetchall()
        return [self._from_row(row) for row in rows]

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
