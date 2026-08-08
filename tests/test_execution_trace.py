from superagent.database.config import DatabaseConfig
from superagent.database.engine import DatabaseEngine
from superagent.database.repositories.sqlite_execution_repository import SqliteExecutionRepository
from superagent.agents.state import AgentStateMachine
from superagent.agents.models import AgentExecutionStatus


def test_execution_trace_persistence(tmp_path):
    db_file = tmp_path / "test_exec.db"
    engine = DatabaseEngine(DatabaseConfig(path=db_file))
    engine.ensure_ready()
    repo = SqliteExecutionRepository(engine)

    sm = AgentStateMachine(execution_id="exec-trace-1", request_id="req-trace-1", execution_repository=repo)
    sm.transition_to(AgentExecutionStatus.ROUTING)
    sm.transition_to(AgentExecutionStatus.COMPLETED)

    saved = repo.get_execution("exec-trace-1")
    assert saved is not None
    assert saved.status == "completed"
    assert "steps" in saved.metadata
    assert len(saved.metadata["steps"]) == 2
