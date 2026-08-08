from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Sequence, Any

from superagent.learning.models import LearningStateModel, LearningStateEnum, ReviewRating, LearningStats, KnowledgeRelationshipModel
from superagent.learning.scheduler import SpacedRepetitionScheduler, StandardFSRSScheduler
from superagent.database.repositories.sqlite_learning_repository import SqliteLearningRepository
from superagent.database.repositories.sqlite_flashcard_repository import SqliteFlashcardRepository
from superagent.database.repositories.sqlite_review_repository import SqliteReviewRepository
from superagent.models.domain import Flashcard, Review


class LearningService:
    """Orchestrates spaced repetition reviews, learning states, and knowledge graph relationships."""

    def __init__(
        self,
        learning_repo: SqliteLearningRepository,
        flashcard_repo: SqliteFlashcardRepository,
        review_repo: SqliteReviewRepository,
        scheduler: SpacedRepetitionScheduler | None = None,
    ) -> None:
        self.learning_repo = learning_repo
        self.flashcard_repo = flashcard_repo
        self.review_repo = review_repo
        self.scheduler = scheduler or StandardFSRSScheduler()

    def get_due_reviews(self, limit: int = 50) -> Sequence[dict[str, Any]]:
        now = datetime.now(timezone.utc)
        due_states = self.learning_repo.list_due_learning_states(now, limit=limit)
        
        # If no learning states exist yet for existing flashcards, initialize them as NEW
        all_flashcards = self.flashcard_repo.list_flashcards()
        existing_state_ids = {s.flashcard_id for s in self.learning_repo.list_learning_states()}
        
        for fc in all_flashcards:
            if fc.flashcard_id not in existing_state_ids:
                initial_state = LearningStateModel(
                    flashcard_id=fc.flashcard_id,
                    state=LearningStateEnum.NEW,
                    due_date=now,
                    created_at=now,
                    updated_at=now,
                )
                self.learning_repo.save_learning_state(initial_state)

        due_states = self.learning_repo.list_due_learning_states(now, limit=limit)
        result = []
        for state in due_states:
            fc = self.flashcard_repo.get_flashcard(state.flashcard_id)
            if fc:
                result.append({
                    "flashcard": fc.model_dump(mode="json"),
                    "learning_state": state.model_dump(mode="json"),
                })
        return result

    def submit_review(self, flashcard_id: str, rating: ReviewRating) -> dict[str, Any]:
        fc = self.flashcard_repo.get_flashcard(flashcard_id)
        if not fc:
            raise ValueError(f"Flashcard not found: {flashcard_id}")

        state = self.learning_repo.get_learning_state(flashcard_id)
        now = datetime.now(timezone.utc)
        if not state:
            state = LearningStateModel(flashcard_id=flashcard_id, due_date=now)

        updated_state, review_record = self.scheduler.schedule(state, rating, reviewed_at=now)
        
        self.learning_repo.save_learning_state(updated_state)
        self.review_repo.create_review(review_record)

        return {
            "flashcard_id": flashcard_id,
            "rating": rating.value,
            "learning_state": updated_state.model_dump(mode="json"),
            "review": review_record.model_dump(mode="json"),
        }

    def get_learning_stats(self) -> LearningStats:
        states = self.learning_repo.list_learning_states()
        flashcards = self.flashcard_repo.list_flashcards()
        
        # Ensure all flashcards have states
        existing_state_ids = {s.flashcard_id for s in states}
        now = datetime.now(timezone.utc)
        for fc in flashcards:
            if fc.flashcard_id not in existing_state_ids:
                s = LearningStateModel(flashcard_id=fc.flashcard_id, due_date=now)
                self.learning_repo.save_learning_state(s)
                states = list(states) + [s]

        total = len(flashcards)
        new_c = sum(1 for s in states if s.state == LearningStateEnum.NEW)
        learning_c = sum(1 for s in states if s.state == LearningStateEnum.LEARNING)
        review_c = sum(1 for s in states if s.state == LearningStateEnum.REVIEW)
        relearning_c = sum(1 for s in states if s.state == LearningStateEnum.RELEARNING)
        due_today = sum(1 for s in states if s.due_date <= now)
        overdue = sum(1 for s in states if s.due_date < now - timedelta(days=1))

        # Count total reviews across all flashcards
        total_reviews = 0
        success_count = 0
        for fc in flashcards:
            revs = self.review_repo.list_reviews_for_flashcard(fc.flashcard_id)
            total_reviews += len(revs)
            for r in revs:
                if r.outcome in ("good", "easy", "correct", "hard"):
                    success_count += 1

        success_rate = (success_count / total_reviews) if total_reviews > 0 else 0.0

        return LearningStats(
            total_cards=total,
            new_cards=new_c,
            learning_cards=learning_c,
            review_cards=review_c,
            relearning_cards=relearning_c,
            due_today=due_today,
            overdue_cards=overdue,
            total_reviews=total_reviews,
            success_rate=success_rate,
        )

    def create_flashcard_with_state(self, flashcard: Flashcard) -> Flashcard:
        self.flashcard_repo.create_flashcard(flashcard)
        now = datetime.now(timezone.utc)
        state = LearningStateModel(
            flashcard_id=flashcard.flashcard_id,
            state=LearningStateEnum.NEW,
            due_date=now,
            created_at=now,
            updated_at=now,
        )
        self.learning_repo.save_learning_state(state)
        return flashcard
