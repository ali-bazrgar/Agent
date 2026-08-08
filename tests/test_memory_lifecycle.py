from superagent.database.config import DatabaseConfig
from superagent.database.engine import DatabaseEngine
from superagent.database.repositories.sqlite_memory_repository import SqliteMemoryRepository
from superagent.memory.lifecycle import MemoryLifecycle


def test_memory_lifecycle_end_to_end(tmp_path):
    db_file = tmp_path / "test_memory.db"
    engine = DatabaseEngine(DatabaseConfig(path=db_file))
    engine.ensure_ready()
    repo = SqliteMemoryRepository(engine)

    lifecycle = MemoryLifecycle(memory_repository=repo)

    processed = lifecycle.process_interaction(
        user_message="My name is Alice and I work at Google",
        assistant_message="Hello Alice!",
        execution_id="exec-100",
    )

    assert len(processed) >= 1
    memories_in_db = repo.list_memories()
    assert len(memories_in_db) >= 1
    assert "Alice" in memories_in_db[0].content
