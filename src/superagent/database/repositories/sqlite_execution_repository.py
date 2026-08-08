from __future__ import annotations

from superagent.core.errors import PersistenceError
from superagent.database.engine import DatabaseEngine
from superagent.models.domain import ExecutionState
from superagent.repositories.ports import ExecutionRepository


class SqliteExecutionRepository(ExecutionRepository):
    def __init__(self, engine: DatabaseEngine) -> None:
        self.engine = engine

    def create_execution(self, execution: ExecutionState) -> ExecutionState:
        try:
            with self.engine.connect() as connection:
                connection.execute(
                    """
                    INSERT INTO executions (
                        id, request_id, status, model_calls, tool_calls, retries,
                        created_at, completed_at, metadata_json
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        execution.execution_id,
                        execution.request_id,
                        execution.status,
                        execution.model_calls,
                        execution.tool_calls,
                        execution.retries,
                        execution.created_at.isoformat(),
                        execution.completed_at.isoformat() if execution.completed_at else None,
                        self.engine.to_json(execution.metadata),
                    ),
                )
                connection.commit()
        except Exception as exc:  # pragma: no cover - defensive branch
            raise PersistenceError(f"failed to create execution: {exc}") from exc
        return execution

    def update_execution(self, execution: ExecutionState) -> ExecutionState:
        try:
            with self.engine.connect() as connection:
                connection.execute(
                    """
                    UPDATE executions
                    SET request_id = ?, status = ?, model_calls = ?, tool_calls = ?, retries = ?,
                        completed_at = ?, metadata_json = ?
                    WHERE id = ?
                    """,
                    (
                        execution.request_id,
                        execution.status,
                        execution.model_calls,
                        execution.tool_calls,
                        execution.retries,
                        execution.completed_at.isoformat() if execution.completed_at else None,
                        self.engine.to_json(execution.metadata),
                        execution.execution_id,
                    ),
                )
                connection.commit()
        except Exception as exc:  # pragma: no cover - defensive branch
            raise PersistenceError(f"failed to update execution: {exc}") from exc
        return execution

    def get_execution(self, execution_id: str) -> ExecutionState | None:
        with self.engine.connect() as connection:
            row = connection.execute("SELECT * FROM executions WHERE id = ?", (execution_id,)).fetchone()
        if row is None:
            return None
        return self._from_row(row)

    def list_executions(self) -> Sequence[ExecutionState]:
        with self.engine.connect() as connection:
            rows = connection.execute("SELECT * FROM executions ORDER BY created_at DESC").fetchall()
        return [self._from_row(row) for row in rows]

    def _from_row(self, row: object) -> ExecutionState:
        from datetime import datetime

        return ExecutionState(
            execution_id=row["id"],
            request_id=row["request_id"],
            status=row["status"],
            model_calls=row["model_calls"],
            tool_calls=row["tool_calls"],
            retries=row["retries"],
            created_at=datetime.fromisoformat(row["created_at"]),
            completed_at=datetime.fromisoformat(row["completed_at"]) if row["completed_at"] else None,
            metadata=self.engine.from_json(row["metadata_json"]) or {},
        )
