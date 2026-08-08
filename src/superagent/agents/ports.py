from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Sequence

from superagent.agents.models import (
    AgentRequest,
    AgentResponse,
    AgentRoute,
    CritiqueResult,
    ExecutionPlan,
    VerificationResult,
)


class AgentRouterPort(ABC):
    """Port for determining request route strategy."""

    @abstractmethod
    def route_request(self, request: AgentRequest) -> AgentRoute: ...


class AgentPlannerPort(ABC):
    """Port for creating bounded execution plans."""

    @abstractmethod
    def create_plan(self, request: AgentRequest, route: AgentRoute) -> ExecutionPlan: ...


class AgentCriticPort(ABC):
    """Port for critiquing LLM-generated answers."""

    @abstractmethod
    def critique(
        self,
        query: str,
        context_str: str,
        response_text: str,
    ) -> CritiqueResult: ...


class AgentVerifierPort(ABC):
    """Port for verifying factual claims against evidence."""

    @abstractmethod
    def verify(
        self,
        query: str,
        candidate_answer: str,
        context_provenance: Sequence[dict[str, Any]],
    ) -> VerificationResult: ...


class AgentOrchestratorPort(ABC):
    """Port for executing agent lifecycle."""

    @abstractmethod
    def execute(self, request: AgentRequest) -> AgentResponse: ...
