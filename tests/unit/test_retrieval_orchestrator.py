from __future__ import annotations

from superagent.retrieval.models import RetrievalCandidate, RetrievalResult
from superagent.retrieval.orchestrator import RetrievalOrchestrator, RetrievalSource


class FakeBackend:
    def __init__(self, candidates: list[RetrievalCandidate], fail: bool = False) -> None:
        self.candidates = candidates
        self.fail = fail

    def retrieve(self, query):
        if self.fail:
            raise RuntimeError("backend unavailable")
        return RetrievalResult(query=query.text, candidates=self.candidates, total_candidates=len(self.candidates))


def candidate(chunk_id: str, score: float) -> RetrievalCandidate:
    return RetrievalCandidate(
        chunk_id=chunk_id,
        document_id=f"doc-{chunk_id}",
        content=f"content {chunk_id}",
        retrieval_score=score,
    )


def test_orchestrator_merges_sources_and_deduplicates() -> None:
    orchestrator = RetrievalOrchestrator(
        {
            RetrievalSource.MEMORY: FakeBackend([candidate("same", 0.8), candidate("memory", 0.7)]),
            RetrievalSource.KNOWLEDGE: FakeBackend([candidate("same", 0.9), candidate("knowledge", 0.6)]),
        }
    )

    result = orchestrator.retrieve(
        "python",
        sources=[RetrievalSource.MEMORY, RetrievalSource.KNOWLEDGE],
        top_k=3,
        candidate_k=6,
    )

    assert [item.chunk_id for item in result.candidates] == ["same", "memory", "knowledge"]
    assert result.candidates[0].provenance["retrieval_source"] == "knowledge"
    assert result.diagnostics.failed_sources == ()
    assert result.diagnostics.candidate_counts == {"memory": 2, "knowledge": 2}


def test_one_source_failure_does_not_hide_successful_sources() -> None:
    orchestrator = RetrievalOrchestrator(
        {
            RetrievalSource.MEMORY: FakeBackend([candidate("memory", 0.7)]),
            RetrievalSource.KNOWLEDGE: FakeBackend([], fail=True),
        }
    )

    result = orchestrator.retrieve(
        "python",
        sources=[RetrievalSource.MEMORY, RetrievalSource.KNOWLEDGE],
        top_k=2,
        candidate_k=4,
    )

    assert [item.chunk_id for item in result.candidates] == ["memory"]
    assert result.diagnostics.executed_sources == (RetrievalSource.MEMORY,)
    assert result.diagnostics.failed_sources == (RetrievalSource.KNOWLEDGE,)


def test_duplicate_requested_sources_are_executed_once() -> None:
    backend = FakeBackend([candidate("memory", 0.7)])
    orchestrator = RetrievalOrchestrator({RetrievalSource.MEMORY: backend})

    result = orchestrator.retrieve(
        "python",
        sources=[RetrievalSource.MEMORY, RetrievalSource.MEMORY],
        top_k=1,
        candidate_k=2,
    )

    assert result.diagnostics.requested_sources == (RetrievalSource.MEMORY,)
    assert result.diagnostics.executed_sources == (RetrievalSource.MEMORY,)
