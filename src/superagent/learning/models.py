from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Any
from pydantic import BaseModel, Field


class ReviewRating(str, Enum):
    AGAIN = "again"
    HARD = "hard"
    GOOD = "good"
    EASY = "easy"


class LearningStateEnum(str, Enum):
    NEW = "new"
    LEARNING = "learning"
    REVIEW = "review"
    RELEARNING = "relearning"


class RelationType(str, Enum):
    RELATED_TO = "related_to"
    PREREQUISITE_OF = "prerequisite_of"
    PART_OF = "part_of"
    CONTRASTS_WITH = "contrasts_with"
    EXAMPLE_OF = "example_of"
    DERIVED_FROM = "derived_from"


class LearningStateModel(BaseModel):
    flashcard_id: str = Field(min_length=1)
    state: LearningStateEnum = LearningStateEnum.NEW
    due_date: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    interval_days: int = Field(default=0, ge=0)
    repetition: int = Field(default=0, ge=0)
    ease_factor: float = Field(default=2.5, ge=1.0)
    stability: float = Field(default=1.0, ge=0.0)
    difficulty: float = Field(default=0.3, ge=0.0, le=1.0)
    last_reviewed_at: datetime | None = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class KnowledgeRelationshipModel(BaseModel):
    relationship_id: str = Field(min_length=1)
    source_id: str = Field(min_length=1)
    target_id: str = Field(min_length=1)
    relation_type: RelationType = RelationType.RELATED_TO
    metadata: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class LearningStats(BaseModel):
    total_cards: int = Field(default=0, ge=0)
    new_cards: int = Field(default=0, ge=0)
    learning_cards: int = Field(default=0, ge=0)
    review_cards: int = Field(default=0, ge=0)
    relearning_cards: int = Field(default=0, ge=0)
    due_today: int = Field(default=0, ge=0)
    overdue_cards: int = Field(default=0, ge=0)
    total_reviews: int = Field(default=0, ge=0)
    success_rate: float = Field(default=0.0, ge=0.0, le=1.0)
