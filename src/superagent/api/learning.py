from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Sequence
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field

from superagent.api.chat import get_container
from superagent.application.container import AppContainer
from superagent.database.repositories.sqlite_learning_repository import SqliteLearningRepository
from superagent.learning.models import LearningStats, ReviewRating
from superagent.learning.service import LearningService
from superagent.models.domain import Flashcard, Source

router = APIRouter(prefix="/learning", tags=["learning"])


def get_learning_service(container: AppContainer = Depends(get_container)) -> LearningService:
    learning_repo = SqliteLearningRepository(container.database_engine)
    return LearningService(
        learning_repo=learning_repo,
        flashcard_repo=container.flashcard_repository,
        review_repo=container.review_repository,
    )


class ReviewSubmitPayload(BaseModel):
    flashcard_id: str = Field(min_length=1)
    rating: ReviewRating


class FlashcardCreatePayload(BaseModel):
    front: str = Field(min_length=1)
    back: str = Field(min_length=1)
    source_id: str | None = None


@router.get("/flashcards", response_model=list[Flashcard])
def list_flashcards(container: AppContainer = Depends(get_container)) -> list[Flashcard]:
    return list(container.flashcard_repository.list_flashcards())


@router.get("/review")
def get_due_reviews_endpoint(
    limit: int = 50,
    service: LearningService = Depends(get_learning_service),
) -> Sequence[dict[str, Any]]:
    limit = min(max(limit, 1), 200)
    return service.get_due_reviews(limit=limit)


@router.post("/review")
def submit_review_endpoint(
    payload: ReviewSubmitPayload,
    service: LearningService = Depends(get_learning_service),
) -> dict[str, Any]:
    try:
        return service.submit_review(payload.flashcard_id, payload.rating)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc


@router.get("/stats", response_model=LearningStats)
def get_learning_stats_endpoint(
    service: LearningService = Depends(get_learning_service),
) -> LearningStats:
    return service.get_learning_stats()


@router.post("/flashcards", response_model=Flashcard, status_code=status.HTTP_200_OK)
def create_flashcard_endpoint(
    payload: FlashcardCreatePayload,
    service: LearningService = Depends(get_learning_service),
) -> Flashcard:
    now = datetime.now(timezone.utc)
    source = Source(
        source_id=payload.source_id or "manual",
        source_type="manual",
        uri=payload.source_id or "manual",
    )
    flashcard = Flashcard(
        flashcard_id=f"fc-{uuid4().hex[:12]}",
        front=payload.front.strip(),
        back=payload.back.strip(),
        source=source,
        difficulty=0.3,
        created_at=now,
        updated_at=now,
    )
    service.create_flashcard_with_state(flashcard)
    return flashcard
