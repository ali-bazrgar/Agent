from datetime import datetime, timezone

from superagent.database.config import DatabaseConfig
from superagent.database.engine import DatabaseEngine
from superagent.database.repositories.sqlite_execution_repository import SqliteExecutionRepository
from superagent.models.domain import ExecutionState


def test_sqlite_execution_repository_exposes_save_execution(tmp_path):
    config = DatabaseConfig(database_path=tmp_path / "test.sqlite3")
    engine = DatabaseEngine(config)
    engine.ensure_ready()
    repository = SqliteExecutionRepository(engine)
    state = ExecutionState(
        execution_id="exec-compat",
        request_id="req-compat",
        status="created",
        created_at=datetime.now(timezone.utc),
        metadata={"compatibility": True},
    )

    saved = repository.save_execution(state)

    assert saved.execution_id == "exec-compat"
    assert repository.get_execution("exec-compat") is not None
    assert hasattr(repository, "save_execution")
