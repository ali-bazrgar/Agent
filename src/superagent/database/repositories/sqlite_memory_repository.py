from __future__ import annotations

from datetime import datetime, timezone
from typing import Sequence

from superagent.core.errors import PersistenceError
from superagent.database.engine import DatabaseEngine
from superagent.models.domain import MemoryRecord, MemoryScope, Source
from superagent.repositories.ports import MemoryRepository


class SqliteMemoryRepository(MemoryRepository):
    def __init__(self, engine: DatabaseEngine) -> None:
        self.engine = engine

    def create_memory(self, memory: MemoryRecord) -> MemoryRecord:
        try:
            with self.engine.connect() as connection:
                scope = memory.scope
                connection.execute("""
                    INSERT INTO memory_records (
                        id, kind, content, confidence, importance, relevance, status,
                        source_type, source_uri, provenance, valid_from, valid_until,
                        created_at, updated_at, structured_data_json, classification,
                        last_accessed_at, access_count, scope_type, owner_id,
                        conversation_id, project_id
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    memory.memory_id, memory.kind.value, memory.content, memory.confidence,
                    memory.importance, memory.relevance, memory.status.value,
                    memory.source.source_type, memory.source.uri, memory.provenance,
                    memory.valid_from.isoformat() if memory.valid_from else None,
                    memory.valid_until.isoformat() if memory.valid_until else None,
                    memory.created_at.isoformat(), memory.updated_at.isoformat(),
                    self.engine.to_json(memory.structured_data), memory.classification,
                    memory.last_accessed_at.isoformat() if memory.last_accessed_at else None,
                    memory.access_count,
                    scope.scope_type.value if scope else "user",
                    scope.owner_id if scope else None,
                    scope.conversation_id if scope else None,
                    scope.project_id if scope else None,
                ))
                connection.commit()
        except Exception as exc:
            raise PersistenceError(f"failed to create memory: {exc}") from exc
        return memory

    def get_memory(self, memory_id: str, scope: MemoryScope | None = None) -> MemoryRecord | None:
        with self.engine.connect() as connection:
            if scope is None:
                row = connection.execute("SELECT * FROM memory_records WHERE id = ?", (memory_id,)).fetchone()
            else:
                row = connection.execute(
                    "SELECT * FROM memory_records WHERE id = ? AND owner_id = ? AND scope_type = ?",
                    (memory_id, scope.owner_id, scope.scope_type.value),
                ).fetchone()
        return self._from_row(row) if row is not None else None

    def list_memories(self, scope: MemoryScope | None = None) -> Sequence[MemoryRecord]:
        with self.engine.connect() as connection:
            if scope is None:
                rows = connection.execute("SELECT * FROM memory_records WHERE status NOT IN ('deleted', 'superseded') ORDER BY created_at").fetchall()
            else:
                rows = connection.execute(
                    "SELECT * FROM memory_records WHERE status NOT IN ('deleted', 'superseded') AND owner_id = ? AND scope_type = ? ORDER BY created_at",
                    (scope.owner_id, scope.scope_type.value),
                ).fetchall()
        return [self._from_row(row) for row in rows]

    def update_memory(self, memory: MemoryRecord) -> MemoryRecord:
        try:
            with self.engine.connect() as connection:
                cursor = connection.execute("""
                    UPDATE memory_records SET kind = ?, content = ?, confidence = ?, importance = ?, relevance = ?,
                        status = ?, source_type = ?, source_uri = ?, provenance = ?, valid_from = ?, valid_until = ?,
                        updated_at = ?, structured_data_json = ?, classification = ?, last_accessed_at = ?, access_count = ?,
                        scope_type = ?, owner_id = ?, conversation_id = ?, project_id = ? WHERE id = ?
                """, (
                    memory.kind.value, memory.content, memory.confidence, memory.importance, memory.relevance,
                    memory.status.value, memory.source.source_type, memory.source.uri, memory.provenance,
                    memory.valid_from.isoformat() if memory.valid_from else None,
                    memory.valid_until.isoformat() if memory.valid_until else None,
                    memory.updated_at.isoformat(), self.engine.to_json(memory.structured_data), memory.classification,
                    memory.last_accessed_at.isoformat() if memory.last_accessed_at else None, memory.access_count,
                    memory.scope.scope_type.value if memory.scope else "user", memory.scope.owner_id if memory.scope else None,
                    memory.scope.conversation_id if memory.scope else None, memory.scope.project_id if memory.scope else None,
                    memory.memory_id,
                ))
                if cursor.rowcount != 1:
                    raise PersistenceError(f"memory not found for update: {memory.memory_id}")
                connection.commit()
        except PersistenceError:
            raise
        except Exception as exc:
            raise PersistenceError(f"failed to update memory: {exc}") from exc
        return memory

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
        owner_id = row["owner_id"]
        scope = MemoryScope(scope_type=row["scope_type"], owner_id=owner_id, conversation_id=row["conversation_id"], project_id=row["project_id"]) if owner_id else None
        return MemoryRecord(
            memory_id=row["id"], kind=row["kind"], content=row["content"],
            structured_data=self.engine.from_json(row["structured_data_json"]), classification=row["classification"],
            confidence=row["confidence"], importance=row["importance"], relevance=row["relevance"], status=row["status"],
            source=Source(source_id=row["id"], source_type=row["source_type"], uri=row["source_uri"]), scope=scope,
            provenance=row["provenance"], valid_from=datetime.fromisoformat(row["valid_from"]) if row["valid_from"] else None,
            valid_until=datetime.fromisoformat(row["valid_until"]) if row["valid_until"] else None,
            last_accessed_at=datetime.fromisoformat(row["last_accessed_at"]) if row["last_accessed_at"] else None,
            access_count=row["access_count"], created_at=datetime.fromisoformat(row["created_at"]), updated_at=datetime.fromisoformat(row["updated_at"]),
        )
