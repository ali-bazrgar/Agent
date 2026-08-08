from __future__ import annotations

import hashlib
from abc import ABC, abstractmethod
from datetime import datetime, timezone

from fsrs import Card, Rating, Scheduler, State

from superagent.learning.models import LearningStateEnum, LearningStateModel, ReviewRating
from superagent.models.domain import Review


class SpacedRepetitionScheduler(ABC):
    @abstractmethod
    def schedule(self, state: LearningStateModel, rating: ReviewRating, reviewed_at: datetime | None = None) -> tuple[LearningStateModel, Review]:
        ...


class StandardFSRSScheduler(SpacedRepetitionScheduler):
    """Deterministic FSRS-6 scheduler backed by the maintained Py-FSRS implementation."""

    def __init__(self, scheduler: Scheduler | None = None) -> None:
        self.scheduler = scheduler or Scheduler(enable_fuzzing=False)

    @staticmethod
    def _card_id(flashcard_id: str) -> int:
        return int.from_bytes(hashlib.sha256(flashcard_id.encode("utf-8")).digest()[:8], "big")

    @classmethod
    def _to_card(cls, state: LearningStateModel) -> Card:
        state_map = {LearningStateEnum.NEW: State.Learning, LearningStateEnum.LEARNING: State.Learning, LearningStateEnum.REVIEW: State.Review, LearningStateEnum.RELEARNING: State.Relearning}
        return Card(
            card_id=cls._card_id(state.flashcard_id),
            state=state_map[state.state],
            step=0 if state.state in (LearningStateEnum.NEW, LearningStateEnum.LEARNING, LearningStateEnum.RELEARNING) else None,
            stability=state.stability if state.stability > 0 else None,
            difficulty=state.difficulty * 10.0 if state.difficulty > 0 else None,
            due=state.due_date,
            last_review=state.last_reviewed_at,
        )

    def schedule(self, state: LearningStateModel, rating: ReviewRating, reviewed_at: datetime | None = None) -> tuple[LearningStateModel, Review]:
        reviewed_at = reviewed_at or datetime.now(timezone.utc)
        if reviewed_at.tzinfo != timezone.utc:
            reviewed_at = reviewed_at.astimezone(timezone.utc)
        rating_map = {ReviewRating.AGAIN: Rating.Again, ReviewRating.HARD: Rating.Hard, ReviewRating.GOOD: Rating.Good, ReviewRating.EASY: Rating.Easy}
        card, review_log = self.scheduler.review_card(self._to_card(state), rating_map[rating], review_datetime=reviewed_at)
        state_map = {State.Learning: LearningStateEnum.LEARNING, State.Review: LearningStateEnum.REVIEW, State.Relearning: LearningStateEnum.RELEARNING}
        interval_days = max(0, (card.due - reviewed_at).days)
        repetition = state.repetition + (0 if rating == ReviewRating.AGAIN and state.state in (LearningStateEnum.NEW, LearningStateEnum.LEARNING) else 1)
        difficulty = min(1.0, max(0.0, (card.difficulty or 3.0) / 10.0))
        stability = max(0.0, card.stability or state.stability)
        updated = LearningStateModel(
            flashcard_id=state.flashcard_id,
            state=state_map[card.state],
            due_date=card.due,
            interval_days=interval_days,
            repetition=repetition,
            ease_factor=max(1.0, state.ease_factor),
            stability=stability,
            difficulty=difficulty,
            last_reviewed_at=reviewed_at,
            created_at=state.created_at,
            updated_at=reviewed_at,
        )
        review = Review(
            review_id=f"rev-{review_log.review_datetime.strftime('%Y%m%d%H%M%S%f')}-{state.flashcard_id[:8]}",
            flashcard_id=state.flashcard_id,
            reviewed_at=reviewed_at,
            outcome=rating.value,
            interval_days=interval_days,
            ease_factor=updated.ease_factor,
        )
        return updated, review
