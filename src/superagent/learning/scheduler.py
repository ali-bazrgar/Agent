from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import datetime, timedelta, timezone
from superagent.learning.models import LearningStateModel, LearningStateEnum, ReviewRating
from superagent.models.domain import Review


class SpacedRepetitionScheduler(ABC):
    """Abstract interface for spaced repetition scheduling algorithms (e.g. FSRS / SM-2)."""

    @abstractmethod
    def schedule(
        self,
        state: LearningStateModel,
        rating: ReviewRating,
        reviewed_at: datetime | None = None,
    ) -> tuple[LearningStateModel, Review]:
        ...


class StandardFSRSScheduler(SpacedRepetitionScheduler):
    """Deterministic FSRS / SM-2 hybrid spaced repetition scheduler."""

    def schedule(
        self,
        state: LearningStateModel,
        rating: ReviewRating,
        reviewed_at: datetime | None = None,
    ) -> tuple[LearningStateModel, Review]:
        reviewed_at = reviewed_at or datetime.now(timezone.utc)
        
        interval = state.interval_days
        repetition = state.repetition
        ease = state.ease_factor
        stability = state.stability
        difficulty = state.difficulty
        current_state = state.state

        if rating == ReviewRating.AGAIN:
            new_state = LearningStateEnum.RELEARNING
            interval = 0
            repetition = 0
            ease = max(1.3, ease - 0.2)
            stability = max(0.1, stability * 0.5)
            difficulty = min(1.0, difficulty + 0.1)
            due_offset_minutes = 10  # re-review same day
            due_date = reviewed_at + timedelta(minutes=due_offset_minutes)
        elif rating == ReviewRating.HARD:
            new_state = LearningStateEnum.LEARNING if current_state == LearningStateEnum.NEW else current_state
            interval = max(1, int(interval * 1.2)) if interval > 0 else 1
            repetition += 1
            ease = max(1.3, ease - 0.15)
            stability = stability * 1.2
            difficulty = min(1.0, difficulty + 0.05)
            due_date = reviewed_at + timedelta(days=interval)
        elif rating == ReviewRating.GOOD:
            new_state = LearningStateEnum.REVIEW
            if interval == 0:
                interval = 1
            elif interval == 1:
                interval = 6
            else:
                interval = max(1, int(interval * ease))
            repetition += 1
            stability = stability * ease
            due_date = reviewed_at + timedelta(days=interval)
        elif rating == ReviewRating.EASY:
            new_state = LearningStateEnum.REVIEW
            ease += 0.15
            if interval == 0:
                interval = 4
            elif interval == 1:
                interval = 10
            else:
                interval = max(1, int(interval * ease * 1.3))
            repetition += 1
            stability = stability * ease * 1.3
            due_date = reviewed_at + timedelta(days=interval)
        else:
            raise ValueError(f"Invalid review rating: {rating}")

        updated_state = LearningStateModel(
            flashcard_id=state.flashcard_id,
            state=new_state,
            due_date=due_date,
            interval_days=interval,
            repetition=repetition,
            ease_factor=ease,
            stability=stability,
            difficulty=difficulty,
            last_reviewed_at=reviewed_at,
            created_at=state.created_at,
            updated_at=reviewed_at,
        )

        from uuid import uuid4
        review_record = Review(
            review_id=f"rev-{uuid4().hex[:12]}",
            flashcard_id=state.flashcard_id,
            reviewed_at=reviewed_at,
            outcome=rating.value,
            interval_days=interval,
            ease_factor=ease,
        )

        return updated_state, review_record
