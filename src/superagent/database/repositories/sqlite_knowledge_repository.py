from __future__ import annotations

from typing import Sequence

from superagent.core.errors import PersistenceError
from superagent.database.engine import DatabaseEngine
from superagent.models.domain import KnowledgeItem
from superagent.repositories.ports import KnowledgeRepository


class SqliteKnowledgeRepository(KnowledgeRepository):
    def __init__(self, engine: DatabaseEngine) -> None:
        self.engine = engine

    def create_knowledge(self, item: KnowledgeItem) -> KnowledgeItem:
        try:
            with self.engine.connect() as connection:
                connection.execute(
                    """
                    INSERT INTO knowledge_items (
                        knowledge_id, kind, title, content, content_hash, source_id,
                        document_id, version_id, chunk_id, metadata_json, provenance_json, created_at, updated_at
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        item.knowledge_id,
                        item.kind,
                        item.title,
                        item.content,
                        item.content_hash,
                        item.source_id,
                        item.document_id,
                        item.version_id,
                        item.chunk_id,
                        self.engine.to_json(item.metadata),
                        self.engine.to_json(item.provenance),
                        item.created_at.isoformat(),
                        item.updated_at.isoformat(),
                    ),
                )
                connection.commit()
        except Exception as exc:  # pragma: no cover - defensive branch
            raise PersistenceError(f"failed to create knowledge item: {exc}") from exc
        return item

    def get_knowledge(self, knowledge_id: str) -> KnowledgeItem | None:
        with self.engine.connect() as connection:
            row = connection.execute(
                "SELECT * FROM knowledge_items WHERE knowledge_id = ?",
                (knowledge_id,),
            ).fetchone()
        if row is None:
            return None
        return self._from_row(row)

    def list_knowledge(self) -> Sequence[KnowledgeItem]:
        with self.engine.connect() as connection:
            rows = connection.execute("SELECT * FROM knowledge_items ORDER BY created_at").fetchall()
        return [self._from_row(row) for row in rows]

    def _from_row(self, row: object) -> KnowledgeItem:
        from datetime import datetime

        return KnowledgeItem(
            knowledge_id=row["knowledge_id"],
            kind=row["kind"],
            title=row["title"],
            content=row["content"],
            content_hash=row["content_hash"],
            source_id=row["source_id"],
            document_id=row["document_id"],
            version_id=row["version_id"],
            chunk_id=row["chunk_id"],
            metadata=self.engine.from_json(row["metadata_json"]) or {},
            provenance=self.engine.from_json(row["provenance_json"]),
            created_at=datetime.fromisoformat(row["created_at"]),
            updated_at=datetime.fromisoformat(row["updated_at"]),
        )
