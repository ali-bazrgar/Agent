from __future__ import annotations

from superagent.retrieval.models import RetrievalCandidate, RetrievalResult
from superagent.retrieval.orchestrator import RetrievalOrchestrator, RetrievalSource
from superagent.retrieval.planner import RetrievalPlanner
from superagent.retrieval.service import RetrievalService


class RecordingBackend:
    def __init__(self) -> None:
        self.last_query = None

    def retrieve(self, query):
        self.last_query = query
        return RetrievalResult(
            query=query.text,
            candidates=[
                RetrievalCandidate(
                    chunk_id="knowledge-1",
                    document_id="doc-1",
                    content="hybrid retrieval content",
                    retrieval_score=0.9,
                )
            ],
            total_candidates=1,
            token_budget=query.token_budget,
            estimated_tokens=5,
        )


def test_service_executes_plan_and_propagates_budget() -> None:
    backend = RecordingBackend()
    service = RetrievalService(
        RetrievalPlanner(),
        RetrievalOrchestrator({RetrievalSource.KNOWLEDGE: backend}),
    )

    execution = service.search("hybrid retrieval", token_budget=512, top_k=3, candidate_k=6)

    assert execution.plan.sources == (RetrievalSource.KNOWLEDGE,)
    assert execution.plan.token_budget == 512
    assert backend.last_query is not None
    assert backend.last_query.token_budget == 512
    assert execution.result.candidates[0].chunk_id == "knowledge-1"
