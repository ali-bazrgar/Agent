from superagent.database.config import DatabaseConfig
from superagent.database.engine import DatabaseEngine
from superagent.database.repositories.sqlite_memory_repository import SqliteMemoryRepository
from superagent.models.domain import MemoryKind, MemoryRecord, MemoryScope, MemoryScopeType, Source


def _repo(tmp_path):
    engine = DatabaseEngine(DatabaseConfig(path=tmp_path / "scope.db"))
    engine.ensure_ready()
    return SqliteMemoryRepository(engine)


def _memory(memory_id: str, owner_id: str, content: str) -> MemoryRecord:
    return MemoryRecord(
        memory_id=memory_id,
        kind=MemoryKind.USER,
        content=content,
        confidence=1.0,
        importance=1.0,
        relevance=1.0,
        source=Source(source_id=f"source-{memory_id}", source_type="agent"),
        scope=MemoryScope(scope_type=MemoryScopeType.USER, owner_id=owner_id),
    )


def test_memory_list_isolated_by_owner(tmp_path):
    repo = _repo(tmp_path)
    repo.create_memory(_memory("m-a", "user-a", "Python"))
    repo.create_memory(_memory("m-b", "user-b", "Rust"))

    a = repo.list_memories(MemoryScope(owner_id="user-a"))
    b = repo.list_memories(MemoryScope(owner_id="user-b"))

    assert [item.content for item in a] == ["Python"]
    assert [item.content for item in b] == ["Rust"]


def test_memory_lookup_cannot_cross_owner_boundary(tmp_path):
    repo = _repo(tmp_path)
    repo.create_memory(_memory("m-a", "user-a", "Python"))

    assert repo.get_memory("m-a", MemoryScope(owner_id="user-b")) is None
    assert repo.get_memory("m-a", MemoryScope(owner_id="user-a")) is not None
