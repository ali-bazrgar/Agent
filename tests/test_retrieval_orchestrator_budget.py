from __future__ import annotations

from superagent.retrieval.models import RetrievalCandidate, RetrievalResult
from superagent.retrieval.orchestrator import RetrievalOrchestrator, RetrievalSource


class StubBackend:
    def __init__(self, candidates: list[RetrievalCandidate]) -> None:
        self.candidates = candidates
        self.received_token_budget: int | None = None

    def retrieve(self, query):
        self.received_token_budget = query.token_budget
        return RetrievalResult(
            query=query.text,
            candidates=self.candidates,
            total_candidates=len(self.candidates),
            estimated_tokens=sum(max(1, (len(c.content) + 3) // 4) for c in self.candidates),
        )


def candidate(chunk_id: str, text: str, score: float) -> RetrievalCandidate:
    return RetrievalCandidate(
        chunk_id=chunk_id,
        document_id=f"doc-{chunk_id}",
        content=text,
        retrieval_score=score,
        retrieval_method="stub",
        provenance={},
        metadata={},
    )


def test_token_budget_is_global_not_split_between_sources() -> None:
    memory = StubBackend([candidate("m1", "m" * 400, 0.4)])
    knowledge = StubBackend([candidate("k1", "k" * 3200, 0.99)])
    orchestrator = RetrievalOrchestrator(
        {
            RetrievalSource.MEMORY: memory,
            RetrievalSource.KNOWLEDGE: knowledge,
        }
    )

    result = orchestrator.retrieve(
        "query",
        sources=(RetrievalSource.MEMORY, RetrievalSource.KNOWLEDGE),
        top_k=2,
        candidate_k=4,
        token_budget=850,
    )

    assert memory.received_token_budget is None
    assert knowledge.received_token_budget is None
    assert [item.chunk_id for item in result.candidates] == ["k1"]
    assert result.diagnostics.token_budgets == {"memory": None, "knowledge": None}
    assert result.diagnostics.total_estimated_tokens <= 850


def test_duplicate_chunk_does_not_consume_budget_twice() -> None:
    duplicate_a = candidate("same", "shared" * 100, 0.4)
    duplicate_b = candidate("same", "shared" * 100, 0.9)
    memory = StubBackend([duplicate_a])
    knowledge = StubBackend([duplicate_b])
    orchestrator = RetrievalOrchestrator(
        {
            RetrievalSource.MEMORY: memory,
            RetrievalSource.KNOWLEDGE: knowledge,
        }
    )

    result = orchestrator.retrieve(
        "query",
        sources=(RetrievalSource.MEMORY, RetrievalSource.KNOWLEDGE),
        top_k=2,
        candidate_k=4,
        token_budget=500,
    )

    assert len(result.candidates) == 1
    assert result.candidates[0].retrieval_score == 0.9
    assert result.diagnostics.total_candidates == 2
