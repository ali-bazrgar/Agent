from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field

from superagent.models.domain import MemoryKind, MemoryRecord, MemoryStatus


class MemoryAction(str, Enum):
    CREATED = "created"
    MERGED = "merged"
    SUPERSEDED = "superseded"
    IGNORED = "ignored"


class MemoryCandidate(BaseModel):
    """Candidate memory extracted from conversation turn."""

    content: str = Field(min_length=1)
    kind: MemoryKind = MemoryKind.SESSION
    importance: float = Field(default=0.5, ge=0.0, le=1.0)
    confidence: float = Field(default=0.5, ge=0.0, le=1.0)
    relevance: float = Field(default=0.5, ge=0.0, le=1.0)
    source_execution_id: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class MemoryPolicy(BaseModel):
    """Configurable thresholds for persisting memory candidates."""

    min_confidence: float = Field(default=0.4, ge=0.0, le=1.0)
    min_importance: float = Field(default=0.3, ge=0.0, le=1.0)
    allowed_kinds: list[MemoryKind] = Field(
        default_factory=lambda: [
            MemoryKind.USER,
            MemoryKind.SEMANTIC,
            MemoryKind.EPISODIC,
            MemoryKind.PROCEDURAL,
            MemoryKind.SESSION,
            MemoryKind.WORKING,
            MemoryKind.TEMPORAL,
        ]
    )


class ConsolidationResult(BaseModel):
    """Result of memory consolidation logic."""

    action: MemoryAction
    memory: MemoryRecord | None = None
    reasoning: str | None = None
