from datetime import datetime, timezone

from superagent.memory.search import MemorySearchQuery, MemorySearchService
from superagent.models.domain import MemoryKind, MemoryRecord, MemoryStatus, Source


class FakeMemoryRepository:
    def __init__(self, memories: list[MemoryRecord]) -> None:
        self.memories = memories

    def list_memories(self):
        return self.memories


def make_memory(memory_id: str, content: str, importance: float = 0.8) -> MemoryRecord:
    now = datetime.now(timezone.utc)
    return MemoryRecord(
        memory_id=memory_id,
        kind=MemoryKind.SEMANTIC,
        content=content,
        confidence=0.9,
        importance=importance,
        relevance=0.8,
        status=MemoryStatus.ACTIVE,
        source=Source(source_id=f"source-{memory_id}", source_type="test"),
        created_at=now,
        updated_at=now,
    )


def test_memory_search_respects_token_budget() -> None:
    memories = [make_memory("1", "RAG retrieval architecture and context management."), make_memory("2", "RAG memory retrieval and reranking.")]
    service = MemorySearchService(FakeMemoryRepository(memories))
    result = service.search(MemorySearchQuery(text="RAG retrieval", limit=10, token_budget=10))
    assert result.estimated_tokens <= 10
    assert len(result.hits) >= 1


def test_memory_search_filters_kind_and_importance() -> None:
    memory = make_memory("1", "important memory", importance=0.9)
    result = MemorySearchService(FakeMemoryRepository([memory])).search(
        MemorySearchQuery(text="important", kinds=(MemoryKind.EPISODIC,), min_importance=0.95)
    )
    assert result.hits == ()
