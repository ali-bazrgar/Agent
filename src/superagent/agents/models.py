from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field, field_validator, model_validator

from superagent.context.models import ChatMessage


class AgentRoute(str, Enum):
    DIRECT = "direct"
    MEMORY = "memory"
    RETRIEVAL = "retrieval"
    RETRIEVAL_AND_MEMORY = "retrieval_and_memory"
    RESEARCH_READY = "research_ready"
    TOOL = "tool"
    RESEARCH = "research"


class AgentExecutionStatus(str, Enum):
    CREATED = "created"
    ROUTING = "routing"
    PLANNING = "planning"
    TOOL_EXECUTION = "tool_execution"
    RETRIEVING = "retrieving"
    CONTEXT_BUILDING = "context_building"
    GENERATING = "generating"
    CRITIQUING = "critiquing"
    VERIFYING = "verifying"
    REVISING = "revising"
    MEMORY_PROCESSING = "memory_processing"
    COMPLETED = "completed"
    FAILED = "failed"


class VerificationStatus(str, Enum):
    SUPPORTED = "supported"
    UNSUPPORTED = "unsupported"
    CONTRADICTED = "contradicted"
    UNKNOWN = "unknown"


class ExecutionStep(BaseModel):
    step_id: str = Field(min_length=1)
    step_name: str = Field(min_length=1)
    status: str = Field(default="pending")
    details: dict[str, Any] = Field(default_factory=dict)
    duration_ms: float = Field(default=0.0, ge=0.0)
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class ExecutionPlan(BaseModel):
    route: AgentRoute
    steps: list[str] = Field(default_factory=list)
    max_iterations: int = Field(default=2, ge=1)
    retrieval_required: bool = False
    memory_required: bool = False
    tool_required: bool = False
    critic_required: bool = True
    verifier_required: bool = True
    revision_allowed: bool = True


class AgentRequest(BaseModel):
    request_id: str = Field(min_length=1)
    conversation_id: str = Field(min_length=1)
    message: str = Field(min_length=1)
    user_id: str | None = None
    system_instructions: list[str] | None = None
    conversation_history: list[ChatMessage] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)
    execution_config: dict[str, Any] = Field(default_factory=dict)

    @field_validator("message")
    @classmethod
    def message_cannot_be_blank(cls, value: str) -> str:
        if not value or not value.strip():
            raise ValueError("Agent message cannot be blank")
        return value.strip()

    @model_validator(mode="after")
    def resolve_runtime_defaults(self) -> "AgentRequest":
        """Fill omitted runtime limits from the single application Settings source.

        Explicit per-request values remain authoritative. This prevents the execution
        engine from silently falling back to a different context/output configuration.
        """
        from superagent.config.settings import get_settings

        settings = get_settings()
        config = dict(self.execution_config)
        config.setdefault("context_window_tokens", settings.context_window_tokens)
        if settings.llm_max_output_tokens is not None:
            config.setdefault("max_tokens", settings.llm_max_output_tokens)
        config.setdefault("temperature", settings.llm_temperature)
        config.setdefault("top_p", settings.llm_top_p)
        self.execution_config = config
        return self


class CritiqueResult(BaseModel):
    passed: bool = True
    score: float = Field(default=1.0, ge=0.0, le=1.0)
    factuality_score: float = Field(default=1.0, ge=0.0, le=1.0)
    relevance_score: float = Field(default=1.0, ge=0.0, le=1.0)
    completeness_score: float = Field(default=1.0, ge=0.0, le=1.0)
    issues: list[str] = Field(default_factory=list)
    required_revision: str | None = None
    reasoning: str | None = None


class VerificationResult(BaseModel):
    verified: bool = True
    status: VerificationStatus = VerificationStatus.SUPPORTED
    confidence: float = Field(default=1.0, ge=0.0, le=1.0)
    supported_claims: list[str] = Field(default_factory=list)
    unsupported_claims: list[str] = Field(default_factory=list)
    contradictory_claims: list[str] = Field(default_factory=list)
    evidence: list[dict[str, Any]] = Field(default_factory=list)


class AgentResponse(BaseModel):
    request_id: str = Field(min_length=1)
    conversation_id: str = Field(min_length=1)
    answer: str = Field(default="")
    execution_id: str = Field(min_length=1)
    status: AgentExecutionStatus = AgentExecutionStatus.COMPLETED
    iterations: int = Field(default=1, ge=1)
    used_retrieval: bool = False
    used_memory: bool = False
    used_tools: bool = False
    used_critic: bool = False
    used_verifier: bool = False
    provenance: list[dict[str, Any]] = Field(default_factory=list)
    diagnostics: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
