from superagent.memory.extraction import MemoryExtractor
from superagent.models.domain import MemoryKind


def test_memory_extraction_user_preference():
    extractor = MemoryExtractor()
    candidates = extractor.extract_candidates(
        user_message="My name is Alice and I prefer Python",
        assistant_message="Nice to meet you Alice!",
        execution_id="exec-1",
    )

    assert len(candidates) >= 1
    assert candidates[0].kind == MemoryKind.USER
    assert "Alice" in candidates[0].content


def test_memory_extraction_ignores_greetings():
    extractor = MemoryExtractor()
    candidates = extractor.extract_candidates(
        user_message="Hello",
        assistant_message="Hi there!",
        execution_id="exec-2",
    )

    assert len(candidates) == 0
