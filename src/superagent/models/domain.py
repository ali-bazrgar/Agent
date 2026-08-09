from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field, field_validator


class MemoryKind(str, Enum):
    WORKING = "working"
    SESSION = "session"
    EPISODIC = "episodic"
    SEMANTIC = "semantic"
    PROCEDURAL = "procedural"
    USER = "user"
    TEMPORAL = "temporal"


class MemoryStatus(str, Enum):
    DRAFT = "draft"
    ACTIVE = "active"
    SUPERSEDED = "superseded"
    EXPIRED = "expired"
    DELETED = "deleted"


class EvidenceLevel(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class Source(BaseModel):
    source_id: str = Field(min_length=1)
    source_type: str = Field(min_length=1)
    uri: str | None = None
    locator: str | None = None
    title: str | None = None
    content_hash: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)
    provenance: dict[str, Any] | None = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class Document(BaseModel):
    document_id: str = Field(min_length=1)
    title: str = Field(min_length=1)
    source: Source
    source_id: str | None = None
    document_type: str = Field(default="document")
    content_type: str | None = None
    content_hash: str | None = None
    status: str = Field(default="active")
    version: int = Field(default=1, ge=1)
    blob_uri: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)
    chunks: list[DocumentChunk] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    @field_validator("title")
    @classmethod
    def title_cannot_be_blank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("title must not be blank")
        return value


class DocumentChunk(BaseModel):
    chunk_id: str = Field(min_length=1)
    document_id: str = Field(min_length=1)
    version_id: str | None = None
    content: str = Field(min_length=1)
    content_hash: str | None = None
    chunk_index: int = Field(ge=0)
    token_count: int | None = Field(default=None, ge=0)
    character_count: int | None = Field(default=None, ge=0)
    language: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class DocumentVersion(BaseModel):
    version_id: str = Field(min_length=1)
    document_id: str = Field(min_length=1)
    title: str | None = None
    content: str | None = None
    content_hash: str | None = None
    content_type: str | None = None
    status: str = Field(default="active")
    metadata: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class EmbeddingRecord(BaseModel):
    embedding_id: str = Field(min_length=1)
    chunk_id: str | None = None
    document_id: str | None = None
    version_id: str | None = None
    model_id: str = Field(min_length=1)
    dimension: int = Field(ge=1)
    vector_json: str = Field(min_length=1)
    content_hash: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class KnowledgeItem(BaseModel):
    knowledge_id: str = Field(min_length=1)
    kind: str = Field(min_length=1)
    title: str | None = None
    content: str | None = None
    content_hash: str | None = None
    source_id: str | None = None
    document_id: str | None = None
    version_id: str | None = None
    chunk_id: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)
    provenance: dict[str, Any] | None = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class Tag(BaseModel):
    tag_id: str = Field(min_length=1)
    resource_type: str = Field(min_length=1)
    resource_id: str = Field(min_length=1)
    name: str = Field(min_length=1)
    value: str | None = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class MemoryRecord(BaseModel):
    memory_id: str = Field(min_length=1)
    kind: MemoryKind
    content: str = Field(min_length=1)
    structured_data: dict[str, Any] = Field(default_factory=dict)
    classification: str = Field(default="explicit", pattern="^(explicit|inferred)$")
    confidence: float = Field(ge=0.0, le=1.0)
    importance: float = Field(ge=0.0, le=1.0)
    relevance: float = Field(ge=0.0, le=1.0)
    status: MemoryStatus = MemoryStatus.ACTIVE
    source: Source
    provenance: str | None = None
    valid_from: datetime | None = None
    valid_until: datetime | None = None
    last_accessed_at: datetime | None = None
    access_count: int = Field(default=0, ge=0)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class ExecutionState(BaseModel):
    execution_id: str = Field(min_length=1)
    request_id: str | None = None
    status: str = Field(default="initialized")
    model_calls: int = Field(default=0, ge=0)
    tool_calls: int = Field(default=0, ge=0)
    retries: int = Field(default=0, ge=0)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    completed_at: datetime | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class Flashcard(BaseModel):
    flashcard_id: str = Field(min_length=1)
    front: str = Field(min_length=1)
    back: str = Field(min_length=1)
    source: Source | None = None
    difficulty: float = Field(default=0.5, ge=0.0, le=1.0)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class Review(BaseModel):
    review_id: str = Field(min_length=1)
    flashcard_id: str = Field(min_length=1)
    reviewed_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    outcome: str = Field(default="correct")
    interval_days: int | None = Field(default=None, ge=0)
    ease_factor: float | None = Field(default=None, ge=0.0)
