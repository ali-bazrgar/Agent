from datetime import datetime, timezone

from superagent.memory.search import MemorySearchService
from superagent.models.domain import MemoryKind, MemoryRecord, MemoryStatus, Source
from superagent.retrieval.memory_backend import MemoryRetrievalBackend
from superagent.retrieval.models import RetrievalFilter, RetrievalQuery
from superagent.retrieval.planner import RetrievalIntent, RetrievalPlanner


class FakeMemoryRepository:
    def __init__(self, memories: list[MemoryRecord]) -> None:
        self.memories = memories

    def list_memories(self):
        return self.memories


def make_memory(memory_id: str, kind: MemoryKind, content: str) -> MemoryRecord:
    now = datetime.now(timezone.utc)
    return MemoryRecord(
        memory_id=memory_id,
        kind=kind,
        content=content,
        confidence=0.9,
        importance=0.8,
        relevance=0.8,
        status=MemoryStatus.ACTIVE,
        source=Source(source_id=f"source-{memory_id}", source_type="test"),
        created_at=now,
        updated_at=now,
    )


def test_memory_backend_propagates_kind_filter_and_budget() -> None:
    repository = FakeMemoryRepository([
        make_memory("semantic", MemoryKind.SEMANTIC, "RAG semantic memory"),
        make_memory("episodic", MemoryKind.EPISODIC, "RAG episodic memory"),
    ])
    backend = MemoryRetrievalBackend(MemorySearchService(repository))
    result = backend.retrieve(
        RetrievalQuery(
            text="RAG memory",
            top_k=5,
            candidate_k=5,
            token_budget=20,
            filters=RetrievalFilter(memory_kinds=["episodic"]),
        )
    )

    assert all(item.metadata["memory_kind"] == "episodic" for item in result.candidates)
    assert result.token_budget == 20
    assert result.estimated_tokens <= 20


def test_planner_selects_memory_kind_from_query() -> None:
    plan = RetrievalPlanner().plan("episodic memory درباره RAG")
    assert plan.intent is RetrievalIntent.MEMORY
    assert plan.filters is not None
    assert plan.filters.memory_kinds == ["episodic"]
