from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from superagent.retrieval.models import RetrievalFilter, RerankConfig
from superagent.retrieval.orchestrator import RetrievalSource


class RetrievalIntent(str, Enum):
    MEMORY = "memory"
    CONVERSATION = "conversation"
    KNOWLEDGE = "knowledge"
    DOCUMENT = "document"
    MIXED = "mixed"
    NONE = "none"


@dataclass(frozen=True)
class RetrievalPlan:
    """Provider-neutral execution plan produced before retrieval starts."""

    intent: RetrievalIntent
    sources: tuple[RetrievalSource, ...]
    top_k: int = 10
    candidate_k: int = 20
    token_budget: int | None = None
    filters: RetrievalFilter | None = None
    rerank: RerankConfig | None = None
    reason: str = ""


class RetrievalPlanner:
    """Deterministic baseline planner.

    This intentionally does not call an LLM. It provides safe, predictable planning
    semantics that a future model-driven planner can replace or extend without
    changing the retrieval contracts.
    """

    def plan(
        self,
        query: str,
        *,
        token_budget: int | None = None,
        top_k: int = 10,
        candidate_k: int = 20,
    ) -> RetrievalPlan:
        normalized = query.strip()
        if not normalized:
            raise ValueError("Retrieval query cannot be empty")
        if top_k < 1:
            raise ValueError("top_k must be at least 1")
        if candidate_k < top_k:
            raise ValueError("candidate_k must be greater than or equal to top_k")
        if token_budget is not None and token_budget < 1:
            raise ValueError("token_budget must be at least 1 when provided")

        lowered = normalized.casefold()
        conversation_markers = (
            "دیروز", "امروز", "قبلاً", "قبلا", "گفتیم", "گفتگو",
            "conversation", "yesterday", "we said",
        )
        memory_markers = (
            "یادم", "یادآوری", "حافظه", "سلیقه", "ترجیح",
            "memory", "remember", "preference",
        )
        document_markers = ("pdf", "فایل", "سند", "document")
        memory_kind_markers = {
            "episodic": "episodic",
            "semantic": "semantic",
            "procedural": "procedural",
            "working": "working",
            "session": "session",
            "user": "user",
            "temporal": "temporal",
        }

        if any(marker in lowered for marker in conversation_markers):
            sources = (RetrievalSource.CONVERSATION,)
            intent = RetrievalIntent.CONVERSATION
            reason = "query contains conversation/time-reference signals"
            filters = None
        elif any(marker in lowered for marker in memory_markers):
            sources = (RetrievalSource.MEMORY,)
            intent = RetrievalIntent.MEMORY
            matched_kinds = [value for marker, value in memory_kind_markers.items() if marker in lowered]
            filters = RetrievalFilter(memory_kinds=matched_kinds or None)
            reason = "query contains memory/personal-context signals"
        elif any(marker in lowered for marker in document_markers):
            sources = (RetrievalSource.DOCUMENT, RetrievalSource.KNOWLEDGE)
            intent = RetrievalIntent.MIXED
            filters = None
            reason = "query contains document/knowledge signals"
        else:
            sources = (RetrievalSource.KNOWLEDGE,)
            intent = RetrievalIntent.KNOWLEDGE
            filters = None
            reason = "default semantic knowledge retrieval"

        return RetrievalPlan(
            intent=intent,
            sources=sources,
            top_k=top_k,
            candidate_k=candidate_k,
            token_budget=token_budget,
            filters=filters,
            rerank=RerankConfig(enabled=True),
            reason=reason,
        )
