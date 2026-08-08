from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any, Sequence

from superagent.database.repositories.sqlite_flashcard_repository import SqliteFlashcardRepository
from superagent.database.repositories.sqlite_learning_repository import SqliteLearningRepository
from superagent.database.repositories.sqlite_review_repository import SqliteReviewRepository
from superagent.learning.models import LearningStateEnum, LearningStateModel, LearningStats, ReviewRating
from superagent.learning.scheduler import SpacedRepetitionScheduler, StandardFSRSScheduler
from superagent.models.domain import Flashcard


class LearningService:
    """Coordinates flashcards, FSRS reviews, due queues and learning analytics."""

    def __init__(self, learning_repo: SqliteLearningRepository, flashcard_repo: SqliteFlashcardRepository, review_repo: SqliteReviewRepository, scheduler: SpacedRepetitionScheduler | None = None) -> None:
        self.learning_repo = learning_repo
        self.flashcard_repo = flashcard_repo
        self.review_repo = review_repo
        self.scheduler = scheduler or StandardFSRSScheduler()

    def _ensure_states(self, now: datetime) -> list[LearningStateModel]:
        states = list(self.learning_repo.list_learning_states())
        known = {state.flashcard_id for state in states}
        for flashcard in self.flashcard_repo.list_flashcards():
            if flashcard.flashcard_id not in known:
                state = LearningStateModel(flashcard_id=flashcard.flashcard_id, state=LearningStateEnum.NEW, due_date=now, created_at=now, updated_at=now)
                self.learning_repo.save_learning_state(state)
                states.append(state)
        return states

    def get_due_reviews(self, limit: int = 50) -> Sequence[dict[str, Any]]:
        if limit < 1:
            return []
        now = datetime.now(timezone.utc)
        self._ensure_states(now)
        due_states = self.learning_repo.list_due_learning_states(now, limit=limit)
        result: list[dict[str, Any]] = []
        for state in due_states:
            flashcard = self.flashcard_repo.get_flashcard(state.flashcard_id)
            if flashcard:
                result.append({"flashcard": flashcard.model_dump(mode="json"), "learning_state": state.model_dump(mode="json")})
        return result

    def submit_review(self, flashcard_id: str, rating: ReviewRating) -> dict[str, Any]:
        if not self.flashcard_repo.get_flashcard(flashcard_id):
            raise ValueError(f"Flashcard not found: {flashcard_id}")
        now = datetime.now(timezone.utc)
        state = self.learning_repo.get_learning_state(flashcard_id) or LearningStateModel(flashcard_id=flashcard_id, due_date=now)
        updated_state, review_record = self.scheduler.schedule(state, rating, reviewed_at=now)
        self.learning_repo.save_learning_state(updated_state)
        self.review_repo.create_review(review_record)
        return {"flashcard_id": flashcard_id, "rating": rating.value, "learning_state": updated_state.model_dump(mode="json"), "review": review_record.model_dump(mode="json")}

    def get_learning_stats(self) -> LearningStats:
        now = datetime.now(timezone.utc)
        states = self._ensure_states(now)
        flashcards = self.flashcard_repo.list_flashcards()
        today = now.date()
        total_reviews = 0
        success_count = 0
        for flashcard in flashcards:
            reviews = self.review_repo.list_reviews_for_flashcard(flashcard.flashcard_id)
            total_reviews += len(reviews)
            success_count += sum(1 for review in reviews if review.outcome in ("hard", "good", "easy", "correct"))
        return LearningStats(
            total_cards=len(flashcards),
            new_cards=sum(s.state == LearningStateEnum.NEW for s in states),
            learning_cards=sum(s.state == LearningStateEnum.LEARNING for s in states),
            review_cards=sum(s.state == LearningStateEnum.REVIEW for s in states),
            relearning_cards=sum(s.state == LearningStateEnum.RELEARNING for s in states),
            due_today=sum(s.due_date.date() == today for s in states if s.due_date <= now),
            overdue_cards=sum(s.due_date < now - timedelta(days=1) for s in states),
            total_reviews=total_reviews,
            success_rate=(success_count / total_reviews) if total_reviews else 0.0,
        )

    def create_flashcard_with_state(self, flashcard: Flashcard) -> Flashcard:
        self.flashcard_repo.create_flashcard(flashcard)
        now = datetime.now(timezone.utc)
        self.learning_repo.save_learning_state(LearningStateModel(flashcard_id=flashcard.flashcard_id, state=LearningStateEnum.NEW, due_date=now, created_at=now, updated_at=now))
        return flashcard
