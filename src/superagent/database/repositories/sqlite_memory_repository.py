from __future__ import annotations

from typing import Sequence

from superagent.core.errors import PersistenceError
from superagent.database.engine import DatabaseEngine
from superagent.models.domain import MemoryRecord, Source
from superagent.repositories.ports import MemoryRepository


class SqliteMemoryRepository(MemoryRepository):
    def __init__(self, engine: DatabaseEngine) -> None:
        self.engine = engine

    def create_memory(self, memory: MemoryRecord) -> MemoryRecord:
        try:
            with self.engine.connect() as connection:
                connection.execute(
                    """
                    INSERT INTO memory_records (
                        id, kind, content, confidence, importance, relevance, status,
                        source_type, source_uri, provenance, valid_from, valid_until,
                        created_at, updated_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        memory.memory_id,
                        memory.kind.value,
                        memory.content,
                        memory.confidence,
                        memory.importance,
                        memory.relevance,
                        memory.status.value,
                        memory.source.source_type,
                        memory.source.uri,
                        memory.provenance,
                        memory.valid_from.isoformat() if memory.valid_from else None,
                        memory.valid_until.isoformat() if memory.valid_until else None,
                        memory.created_at.isoformat(),
                        memory.updated_at.isoformat(),
                    ),
                )
                connection.commit()
        except Exception as exc:  # pragma: no cover - defensive branch
            raise PersistenceError(f"failed to create memory: {exc}") from exc
        return memory

    def get_memory(self, memory_id: str) -> MemoryRecord | None:
        with self.engine.connect() as connection:
            row = connection.execute("SELECT * FROM memory_records WHERE id = ?", (memory_id,)).fetchone()
        if row is None:
            return None
        return self._from_row(row)

    def list_memories(self) -> Sequence[MemoryRecord]:
        with self.engine.connect() as connection:
            rows = connection.execute("SELECT * FROM memory_records ORDER BY created_at").fetchall()
        return [self._from_row(row) for row in rows]

    def _from_row(self, row: object) -> MemoryRecord:
        from datetime import datetime

        return MemoryRecord(
            memory_id=row["id"],
            kind=row["kind"],
            content=row["content"],
            confidence=row["confidence"],
            importance=row["importance"],
            relevance=row["relevance"],
            status=row["status"],
            source=Source(source_id=row["id"], source_type=row["source_type"], uri=row["source_uri"]),
            provenance=row["provenance"],
            valid_from=datetime.fromisoformat(row["valid_from"]) if row["valid_from"] else None,
            valid_until=datetime.fromisoformat(row["valid_until"]) if row["valid_until"] else None,
            created_at=datetime.fromisoformat(row["created_at"]),
            updated_at=datetime.fromisoformat(row["updated_at"]),
        )
