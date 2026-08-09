from superagent.database.config import DatabaseConfig
from superagent.database.engine import DatabaseEngine
from superagent.database.repositories.sqlite_memory_repository import SqliteMemoryRepository
from superagent.memory.lifecycle import MemoryLifecycle
from superagent.memory.extraction import MemoryExtractor
from superagent.models.domain import MemoryKind, MemoryStatus


def _repo(tmp_path):
    db_file = tmp_path / "test_memory.db"
    engine = DatabaseEngine(DatabaseConfig(path=db_file))
    engine.ensure_ready()
    return SqliteMemoryRepository(engine)


def _process_legacy(lifecycle, **kwargs):
    return lifecycle.process_interaction(enable_heuristic_extraction=True, **kwargs)


def test_memory_lifecycle_end_to_end(tmp_path):
    repo = _repo(tmp_path)
    lifecycle = MemoryLifecycle(memory_repository=repo)

    processed = _process_legacy(
        lifecycle,
        user_message="My name is Alice and I work at Google",
        assistant_message="Hello Alice!",
        execution_id="exec-100",
    )

    assert len(processed) >= 1
    memories_in_db = repo.list_memories()
    assert len(memories_in_db) >= 1
    assert "Alice" in memories_in_db[0].content


def test_persian_explicit_memory_is_persisted(tmp_path):
    repo = _repo(tmp_path)
    lifecycle = MemoryLifecycle(memory_repository=repo)

    processed = _process_legacy(
        lifecycle,
        user_message="این اطلاعات رو ذخیره کن: پایتون زبان خوبی هست. من پایتون را دوست دارم.",
        assistant_message="اطلاعات را دریافت کردم.",
        execution_id="exec-fa-1",
    )

    assert len(processed) == 1
    assert processed[0].kind == MemoryKind.USER
    assert "پایتون" in processed[0].content
    assert "ذخیره" not in processed[0].content
    assert repo.get_memory(processed[0].memory_id) is not None


def test_merge_updates_existing_memory_instead_of_duplicate_insert(tmp_path):
    repo = _repo(tmp_path)
    lifecycle = MemoryLifecycle(memory_repository=repo)

    first = _process_legacy(
        lifecycle,
        user_message="My name is Alice",
        assistant_message="Noted.",
        execution_id="exec-1",
    )
    assert len(first) == 1

    second = _process_legacy(
        lifecycle,
        user_message="My name is Alice",
        assistant_message="Noted again.",
        execution_id="exec-2",
    )

    assert len(second) == 1
    assert second[0].memory_id == first[0].memory_id
    assert len(repo.list_memories()) == 1
    assert repo.get_memory(first[0].memory_id).confidence > first[0].confidence


def test_superseded_memory_is_removed_from_active_list(tmp_path):
    repo = _repo(tmp_path)
    lifecycle = MemoryLifecycle(memory_repository=repo)

    first = _process_legacy(
        lifecycle,
        user_message="My name is Alice",
        assistant_message="Noted.",
        execution_id="exec-1",
    )
    assert len(first) == 1

    second = _process_legacy(
        lifecycle,
        user_message="My name is Bob",
        assistant_message="Noted.",
        execution_id="exec-2",
    )

    assert len(second) == 1
    assert second[0].content == "My name is Bob"
    assert repo.get_memory(first[0].memory_id).status == MemoryStatus.SUPERSEDED
    assert [m.content for m in repo.list_memories()] == ["My name is Bob"]


def test_extractor_does_not_store_a_bare_question():
    extractor = MemoryExtractor()
    assert extractor.extract_candidates("این را ذخیره کن: چرا پایتون خوب است؟", "") == []


def test_memory_lifecycle_is_non_heuristic_by_default(tmp_path):
    repo = _repo(tmp_path)
    lifecycle = MemoryLifecycle(memory_repository=repo)

    processed = lifecycle.process_interaction(
        user_message="این اطلاعات رو ذخیره کن: پایتون زبان خوبی هست.",
        assistant_message="باشه.",
        execution_id="exec-default-off",
    )

    assert processed == []
    assert repo.list_memories() == []
