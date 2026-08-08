from __future__ import annotations

from typing import Sequence

from superagent.core.errors import PersistenceError
from superagent.database.engine import DatabaseEngine
from superagent.models.domain import DocumentVersion
from superagent.repositories.ports import DocumentVersionRepository


class SqliteDocumentVersionRepository(DocumentVersionRepository):
    def __init__(self, engine: DatabaseEngine) -> None:
        self.engine = engine

    def create_version(self, version: DocumentVersion) -> DocumentVersion:
        try:
            with self.engine.connect() as connection:
                connection.execute(
                    """
                    INSERT INTO document_versions (
                        version_id, document_id, title, content, content_hash,
                        content_type, status, metadata_json, created_at, updated_at
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        version.version_id,
                        version.document_id,
                        version.title,
                        version.content,
                        version.content_hash,
                        version.content_type,
                        version.status,
                        self.engine.to_json(version.metadata),
                        version.created_at.isoformat(),
                        version.updated_at.isoformat(),
                    ),
                )
                connection.commit()
        except Exception as exc:  # pragma: no cover - defensive branch
            raise PersistenceError(f"failed to create document version: {exc}") from exc
        return version

    def get_version(self, version_id: str) -> DocumentVersion | None:
        with self.engine.connect() as connection:
            row = connection.execute(
                "SELECT * FROM document_versions WHERE version_id = ?",
                (version_id,),
            ).fetchone()
        if row is None:
            return None
        return self._from_row(row)

    def list_versions_for_document(self, document_id: str) -> Sequence[DocumentVersion]:
        with self.engine.connect() as connection:
            rows = connection.execute(
                "SELECT * FROM document_versions WHERE document_id = ? ORDER BY created_at",
                (document_id,),
            ).fetchall()
        return [self._from_row(row) for row in rows]

    def _from_row(self, row: object) -> DocumentVersion:
        from datetime import datetime

        return DocumentVersion(
            version_id=row["version_id"],
            document_id=row["document_id"],
            title=row["title"],
            content=row["content"],
            content_hash=row["content_hash"],
            content_type=row["content_type"],
            status=row["status"],
            metadata=self.engine.from_json(row["metadata_json"]) or {},
            created_at=datetime.fromisoformat(row["created_at"]),
            updated_at=datetime.fromisoformat(row["updated_at"]),
        )
