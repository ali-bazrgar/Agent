from __future__ import annotations

from dataclasses import dataclass

from superagent.retrieval.models import RetrievalFilter
from superagent.retrieval.orchestrator import OrchestratedRetrievalResult, RetrievalOrchestrator
from superagent.retrieval.planner import RetrievalPlan, RetrievalPlanner


@dataclass(frozen=True)
class RetrievalExecution:
    plan: RetrievalPlan
    result: OrchestratedRetrievalResult


class RetrievalService:
    """Application service joining planning and provider-neutral retrieval."""

    def __init__(self, planner: RetrievalPlanner, orchestrator: RetrievalOrchestrator) -> None:
        self.planner = planner
        self.orchestrator = orchestrator

    def search(
        self,
        query: str,
        *,
        token_budget: int | None = None,
        top_k: int = 10,
        candidate_k: int = 20,
        filters: RetrievalFilter | None = None,
    ) -> RetrievalExecution:
        plan = self.planner.plan(
            query,
            token_budget=token_budget,
            top_k=top_k,
            candidate_k=candidate_k,
        )
        result = self.orchestrator.retrieve(
            query,
            sources=plan.sources,
            top_k=plan.top_k,
            candidate_k=plan.candidate_k,
            token_budget=plan.token_budget,
            filters=filters or plan.filters,
            rerank_config=plan.rerank,
        )
        return RetrievalExecution(plan=plan, result=result)
