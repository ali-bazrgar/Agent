from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field, field_validator

from superagent.models.domain import MemoryRecord
from superagent.retrieval.models import RetrievalResult


class ContextItemKind(str, Enum):
    SYSTEM_INSTRUCTION = "system_instruction"
    USER_QUERY = "user_query"
    CONVERSATION_MESSAGE = "conversation_message"
    MEMORY = "memory"
    KNOWLEDGE_CHUNK = "knowledge_chunk"
    TOOL_RESULT = "tool_result"
    RESEARCH_EVIDENCE = "research_evidence"


class ChatMessage(BaseModel):
    """Structured chat message compatible with LLM providers."""

    role: str = Field(min_length=1)
    content: str = Field(default="")
    name: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)

    @field_validator("role")
    @classmethod
    def validate_role(cls, value: str) -> str:
        valid_roles = {"system", "user", "assistant", "tool"}
        if value.lower() not in valid_roles:
            raise ValueError(f"Invalid message role '{value}'. Must be one of {valid_roles}")
        return value.lower()


class ContextItem(BaseModel):
    """Individual unit of context managed by the Context Engine."""

    item_id: str = Field(min_length=1)
    kind: ContextItemKind
    content: str = Field(min_length=1)
    priority: int = Field(default=50)
    score: float = Field(default=0.0)
    estimated_tokens: int = Field(default=0, ge=0)
    source_id: str | None = None
    document_id: str | None = None
    version_id: str | None = None
    chunk_id: str | None = None
    memory_id: str | None = None
    retrieval_method: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)
    provenance: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class ContextBudget(BaseModel):
    """Configuration for token allocation across context categories."""

    total_context_window: int = Field(default=8192, ge=1)
    reserved_output_tokens: int = Field(default=1024, ge=0)
    system_budget: int | None = Field(default=None, ge=1)
    conversation_budget: int | None = Field(default=None, ge=1)
    memory_budget: int | None = Field(default=None, ge=1)
    knowledge_budget: int | None = Field(default=None, ge=1)
    query_budget: int | None = Field(default=None, ge=1)

    @property
    def available_prompt_tokens(self) -> int:
        return max(0, self.total_context_window - self.reserved_output_tokens)


class ContextRequest(BaseModel):
    """Input payload for deterministic context construction."""

    query: str = Field(min_length=1)
    system_instructions: list[str] | None = None
    conversation_history: list[ChatMessage] = Field(default_factory=list)
    retrieval_result: RetrievalResult | None = None
    retrieval_candidates: list[ContextItem] = Field(default_factory=list)
    memories: list[MemoryRecord] | None = None
    budget: ContextBudget = Field(default_factory=ContextBudget)
    metadata: dict[str, Any] = Field(default_factory=dict)

    @field_validator("query")
    @classmethod
    def query_cannot_be_blank(cls, value: str) -> str:
        if not value or not value.strip():
            raise ValueError("Context request query cannot be blank")
        return value.strip()


class ContextSelection(BaseModel):
    selected_items: list[ContextItem] = Field(default_factory=list)
    dropped_items: list[ContextItem] = Field(default_factory=list)
    allocated_tokens: dict[str, int] = Field(default_factory=dict)
    total_selected_tokens: int = 0


class ContextBuildResult(BaseModel):
    prompt_messages: list[ChatMessage] = Field(default_factory=list)
    selection: ContextSelection
    total_prompt_tokens: int = 0
    reserved_output_tokens: int = 0
    total_context_window: int = 0
    provenance: list[dict[str, Any]] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)
