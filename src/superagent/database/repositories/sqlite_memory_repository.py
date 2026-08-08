from __future__ import annotations

from datetime import datetime, timezone
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
                        created_at, updated_at, structured_data_json, classification,
                        last_accessed_at, access_count
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        memory.memory_id, memory.kind.value, memory.content, memory.confidence,
                        memory.importance, memory.relevance, memory.status.value,
                        memory.source.source_type, memory.source.uri, memory.provenance,
                        memory.valid_from.isoformat() if memory.valid_from else None,
                        memory.valid_until.isoformat() if memory.valid_until else None,
                        memory.created_at.isoformat(), memory.updated_at.isoformat(),
                        self.engine.to_json(memory.structured_data), memory.classification,
                        memory.last_accessed_at.isoformat() if memory.last_accessed_at else None,
                        memory.access_count,
                    ),
                )
                connection.commit()
        except Exception as exc:
            raise PersistenceError(f"failed to create memory: {exc}") from exc
        return memory

    def get_memory(self, memory_id: str) -> MemoryRecord | None:
        with self.engine.connect() as connection:
            row = connection.execute("SELECT * FROM memory_records WHERE id = ?", (memory_id,)).fetchone()
        return self._from_row(row) if row is not None else None

    def list_memories(self) -> Sequence[MemoryRecord]:
        with self.engine.connect() as connection:
            rows = connection.execute("SELECT * FROM memory_records WHERE status NOT IN ('deleted', 'superseded') ORDER BY created_at").fetchall()
        return [self._from_row(row) for row in rows]

    def mark_accessed(self, memory_id: str) -> None:
        now = datetime.now(timezone.utc).isoformat()
        with self.engine.connect() as connection:
            connection.execute("UPDATE memory_records SET last_accessed_at = ?, access_count = access_count + 1, updated_at = ? WHERE id = ?", (now, now, memory_id))
            connection.commit()

    def update_status(self, memory_id: str, status: str) -> None:
        now = datetime.now(timezone.utc).isoformat()
        with self.engine.connect() as connection:
            connection.execute("UPDATE memory_records SET status = ?, updated_at = ? WHERE id = ?", (status, now, memory_id))
            connection.commit()

    def _from_row(self, row: object) -> MemoryRecord:
        return MemoryRecord(
            memory_id=row["id"], kind=row["kind"], content=row["content"],
            structured_data=self.engine.from_json(row["structured_data_json"]),
            classification=row["classification"], confidence=row["confidence"],
            importance=row["importance"], relevance=row["relevance"], status=row["status"],
            source=Source(source_id=row["id"], source_type=row["source_type"], uri=row["source_uri"]),
            provenance=row["provenance"],
            valid_from=datetime.fromisoformat(row["valid_from"]) if row["valid_from"] else None,
            valid_until=datetime.fromisoformat(row["valid_until"]) if row["valid_until"] else None,
            last_accessed_at=datetime.fromisoformat(row["last_accessed_at"]) if row["last_accessed_at"] else None,
            access_count=row["access_count"],
            created_at=datetime.fromisoformat(row["created_at"]),
            updated_at=datetime.fromisoformat(row["updated_at"]),
        )
