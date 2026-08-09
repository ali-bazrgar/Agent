from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field, field_validator, model_validator

from superagent.context.models import ChatMessage
from superagent.llm.runtime import ModelRuntimeConfig


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
    memory_recall_every_message: bool = True
    tool_required: bool = False
    critic_required: bool = True
    verifier_required: bool = True
    revision_allowed: bool = True

    @model_validator(mode="after")
    def apply_memory_recall_policy(self) -> "ExecutionPlan":
        if self.memory_recall_every_message:
            self.memory_required = True
            if "RETRIEVING" not in self.steps:
                insert_at = self.steps.index("CONTEXT_BUILDING") if "CONTEXT_BUILDING" in self.steps else len(self.steps)
                self.steps.insert(insert_at, "RETRIEVING")
        return self


class AgentRequest(BaseModel):
    request_id: str = Field(min_length=1)
    conversation_id: str = Field(min_length=1)
    message: str = Field(min_length=1)
    user_id: str | None = None
    system_instructions: list[str] | None = None
    conversation_history: list[ChatMessage] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)
    execution_config: dict[str, Any] = Field(default_factory=dict)
    runtime_config: ModelRuntimeConfig | None = Field(default=None, exclude=True, repr=False)

    @field_validator("message")
    @classmethod
    def message_cannot_be_blank(cls, value: str) -> str:
        if not value or not value.strip():
            raise ValueError("Agent message cannot be blank")
        return value.strip()

    @model_validator(mode="after")
    def resolve_runtime_defaults(self) -> "AgentRequest":
        """Resolve safe execution defaults from the application runtime."""
        config = dict(self.execution_config)
        config.setdefault("memory_recall_every_message", True)
        config.setdefault("memory_recall_top_k", 5)
        if self.runtime_config is not None:
            config.setdefault("context_window_tokens", self.runtime_config.context_window_tokens)
            if self.runtime_config.max_output_tokens is not None:
                config.setdefault("max_tokens", self.runtime_config.max_output_tokens)
            config.setdefault("temperature", self.runtime_config.temperature)
            config.setdefault("top_p", self.runtime_config.top_p)
        self.execution_config = config
        return self
