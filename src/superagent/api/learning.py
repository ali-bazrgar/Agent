from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Sequence
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field

from superagent.api.chat import get_container
from superagent.application.container import AppContainer
from superagent.database.repositories.sqlite_learning_repository import SqliteLearningRepository
from superagent.learning.models import KnowledgeRelationshipModel, LearningStats, RelationType, ReviewRating
from superagent.learning.service import LearningService
from superagent.models.domain import Flashcard, Source

router = APIRouter(prefix="/learning", tags=["learning"])


def get_learning_repository(container: AppContainer = Depends(get_container)) -> SqliteLearningRepository:
    return SqliteLearningRepository(container.database_engine)


def get_learning_service(container: AppContainer = Depends(get_container)) -> LearningService:
    return LearningService(
        learning_repo=get_learning_repository(container),
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


class RelationshipCreatePayload(BaseModel):
    source_id: str = Field(min_length=1)
    target_id: str = Field(min_length=1)
    relation_type: RelationType = RelationType.RELATED_TO
    metadata: dict[str, Any] = Field(default_factory=dict)


@router.get("/review")
def get_due_reviews_endpoint(
    limit: int = 50,
    service: LearningService = Depends(get_learning_service),
) -> Sequence[dict[str, Any]]:
    limit = max(1, min(limit, 500))
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


@router.post("/flashcards")
def create_flashcard_endpoint(
    payload: FlashcardCreatePayload,
    service: LearningService = Depends(get_learning_service),
) -> dict[str, Any]:
    fc_id = f"fc-{uuid4().hex[:12]}"
    now = datetime.now(timezone.utc)
    source = Source(source_id=payload.source_id or "manual", source_type="manual", uri=payload.source_id or "manual")
    fc = Flashcard(
        flashcard_id=fc_id,
        front=payload.front,
        back=payload.back,
        source=source,
        difficulty=0.3,
        created_at=now,
        updated_at=now,
    )
    service.create_flashcard_with_state(fc)
    return fc.model_dump(mode="json")


@router.post("/relationships")
def create_relationship_endpoint(
    payload: RelationshipCreatePayload,
    repository: SqliteLearningRepository = Depends(get_learning_repository),
) -> dict[str, Any]:
    if payload.source_id == payload.target_id:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="source_id and target_id must be different",
        )
    relationship = KnowledgeRelationshipModel(
        relationship_id=f"rel-{uuid4().hex[:12]}",
        source_id=payload.source_id,
        target_id=payload.target_id,
        relation_type=payload.relation_type,
        metadata=payload.metadata,
    )
    return repository.create_knowledge_relationship(relationship).model_dump(mode="json")


@router.get("/relationships/{resource_id}")
def list_relationships_endpoint(
    resource_id: str,
    repository: SqliteLearningRepository = Depends(get_learning_repository),
) -> Sequence[KnowledgeRelationshipModel]:
    if not resource_id.strip():
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="resource_id is required")
    return repository.list_knowledge_relationships(resource_id)
