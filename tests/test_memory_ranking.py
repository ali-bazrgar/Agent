from superagent.memory.ranking import MemoryRanker
from superagent.models.domain import MemoryKind, MemoryRecord, MemoryStatus, Source


def test_memory_ranker_sorting():
    mem1 = MemoryRecord(
        memory_id="mem-1",
        kind=MemoryKind.USER,
        content="I prefer Python programming",
        confidence=0.9,
        importance=0.9,
        relevance=0.8,
        status=MemoryStatus.ACTIVE,
        source=Source(source_id="src-1", source_type="user", uri=""),
    )
    mem2 = MemoryRecord(
        memory_id="mem-2",
        kind=MemoryKind.USER,
        content="I like apples",
        confidence=0.5,
        importance=0.5,
        relevance=0.5,
        status=MemoryStatus.ACTIVE,
        source=Source(source_id="src-2", source_type="user", uri=""),
    )

    ranked = MemoryRanker.rank_memories([mem1, mem2], query_text="Python programming", top_k=5)

    assert len(ranked) == 2
    assert ranked[0].memory_id == "mem-1"
