from __future__ import annotations

from typing import Sequence

from superagent.core.errors import PersistenceError
from superagent.database.engine import DatabaseEngine
from superagent.models.domain import Review
from superagent.repositories.ports import ReviewRepository


class SqliteReviewRepository(ReviewRepository):
    def __init__(self, engine: DatabaseEngine) -> None:
        self.engine = engine

    def create_review(self, review: Review) -> Review:
        try:
            with self.engine.connect() as connection:
                connection.execute(
                    """
                    INSERT INTO reviews (id, flashcard_id, reviewed_at, outcome, interval_days, ease_factor)
                    VALUES (?, ?, ?, ?, ?, ?)
                    """,
                    (
                        review.review_id,
                        review.flashcard_id,
                        review.reviewed_at.isoformat(),
                        review.outcome,
                        review.interval_days,
                        review.ease_factor,
                    ),
                )
                connection.commit()
        except Exception as exc:  # pragma: no cover - defensive branch
            raise PersistenceError(f"failed to create review: {exc}") from exc
        return review

    def list_reviews_for_flashcard(self, flashcard_id: str) -> Sequence[Review]:
        with self.engine.connect() as connection:
            rows = connection.execute(
                "SELECT * FROM reviews WHERE flashcard_id = ? ORDER BY reviewed_at",
                (flashcard_id,),
            ).fetchall()
        return [self._from_row(row) for row in rows]

    def _from_row(self, row: object) -> Review:
        from datetime import datetime

        return Review(
            review_id=row["id"],
            flashcard_id=row["flashcard_id"],
            reviewed_at=datetime.fromisoformat(row["reviewed_at"]),
            outcome=row["outcome"],
            interval_days=row["interval_days"],
            ease_factor=row["ease_factor"],
        )
