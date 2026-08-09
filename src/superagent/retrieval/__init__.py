"""Retrieval package public API.

Imports are intentionally lazy so importing ``superagent.retrieval.models`` does
not eagerly import every retrieval backend. This keeps the domain/model layer
free of package-initialization side effects and prevents circular imports.
"""

from __future__ import annotations

from importlib import import_module
from typing import Any

_EXPORTS: dict[str, tuple[str, str]] = {
    "CandidateFusion": ("superagent.retrieval.ports", "CandidateFusion"),
    "DenseRetriever": ("superagent.retrieval.ports", "DenseRetriever"),
    "GlobalRankingConfig": ("superagent.retrieval.ranking", "GlobalRankingConfig"),
    "GlobalRetrievalRanker": ("superagent.retrieval.ranking", "GlobalRetrievalRanker"),
    "HybridRetriever": ("superagent.retrieval.pipeline", "HybridRetriever"),
    "LexicalRetriever": ("superagent.retrieval.ports", "LexicalRetriever"),
    "MemoryRetrievalBackend": ("superagent.retrieval.memory_backend", "MemoryRetrievalBackend"),
    "OrchestratedRetrievalResult": ("superagent.retrieval.orchestrator", "OrchestratedRetrievalResult"),
    "RankedCandidate": ("superagent.retrieval.ranking", "RankedCandidate"),
    "ReciprocalRankFusion": ("superagent.retrieval.fusion", "ReciprocalRankFusion"),
    "RerankConfig": ("superagent.retrieval.models", "RerankConfig"),
    "RetrievalCandidate": ("superagent.retrieval.models", "RetrievalCandidate"),
    "RetrievalDiagnostics": ("superagent.retrieval.orchestrator", "RetrievalDiagnostics"),
    "RetrievalExecution": ("superagent.retrieval.service", "RetrievalExecution"),
    "RetrievalFilter": ("superagent.retrieval.models", "RetrievalFilter"),
    "RetrievalIntent": ("superagent.retrieval.planner", "RetrievalIntent"),
    "RetrievalOrchestrator": ("superagent.retrieval.orchestrator", "RetrievalOrchestrator"),
    "RetrievalPlan": ("superagent.retrieval.planner", "RetrievalPlan"),
    "RetrievalPlanner": ("superagent.retrieval.planner", "RetrievalPlanner"),
    "RetrievalQuery": ("superagent.retrieval.models", "RetrievalQuery"),
    "RetrievalResult": ("superagent.retrieval.models", "RetrievalResult"),
    "RetrievalService": ("superagent.retrieval.service", "RetrievalService"),
    "RetrievalSource": ("superagent.retrieval.orchestrator", "RetrievalSource"),
    "RetrievalSourceBackend": ("superagent.retrieval.orchestrator", "RetrievalSourceBackend"),
    "SqliteDenseRetriever": ("superagent.retrieval.dense", "SqliteDenseRetriever"),
    "SqliteLexicalRetriever": ("superagent.retrieval.lexical", "SqliteLexicalRetriever"),
}

__all__ = sorted(_EXPORTS)


def __getattr__(name: str) -> Any:
    target = _EXPORTS.get(name)
    if target is None:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
    module_name, attribute_name = target
    value = getattr(import_module(module_name), attribute_name)
    globals()[name] = value
    return value


def __dir__() -> list[str]:
    return sorted(set(globals()) | set(__all__))
