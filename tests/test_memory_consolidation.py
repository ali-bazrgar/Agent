from datetime import datetime, timezone

from superagent.memory.consolidation import MemoryConsolidator
from superagent.memory.models import MemoryAction, MemoryCandidate
from superagent.models.domain import MemoryKind, MemoryRecord, MemoryStatus, Source


def test_memory_consolidation_new_record():
    consolidator = MemoryConsolidator()
    cand = MemoryCandidate(content="I like coffee", kind=MemoryKind.USER)

    res = consolidator.consolidate(cand, existing_memories=[])

    assert res.action == MemoryAction.CREATED
    assert res.memory is not None
    assert res.memory.content == "I like coffee"


def test_memory_consolidation_exact_duplicate_merge():
    consolidator = MemoryConsolidator()
    existing = MemoryRecord(
        memory_id="mem-1",
        kind=MemoryKind.USER,
        content="I like coffee",
        confidence=0.5,
        importance=0.5,
        relevance=0.5,
        status=MemoryStatus.ACTIVE,
        source=Source(source_id="src-1", source_type="user", uri=""),
    )
    cand = MemoryCandidate(content="I like coffee", kind=MemoryKind.USER)

    res = consolidator.consolidate(cand, existing_memories=[existing])

    assert res.action == MemoryAction.MERGED
    assert res.memory is not None
    assert res.memory.confidence == 0.6  # boosted from 0.5
