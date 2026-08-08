from __future__ import annotations

import pytest
from datetime import datetime, timezone
from fastapi.testclient import TestClient

from superagent.database.config import DatabaseConfig
from superagent.database.engine import DatabaseEngine
from superagent.database.repositories.sqlite_flashcard_repository import SqliteFlashcardRepository
from superagent.database.repositories.sqlite_review_repository import SqliteReviewRepository
from superagent.database.repositories.sqlite_learning_repository import SqliteLearningRepository
from superagent.learning.models import LearningStateModel, LearningStateEnum, ReviewRating, KnowledgeRelationshipModel, RelationType
from superagent.learning.scheduler import StandardFSRSScheduler
from superagent.learning.service import LearningService
from superagent.models.domain import Flashcard, Source
from superagent.api.app import create_app


@pytest.fixture
def temp_db(tmp_path):
    db_path = tmp_path / "test_learning.sqlite3"
    config = DatabaseConfig(path=db_path, timeout_seconds=5.0)
    engine = DatabaseEngine(config)
    engine.ensure_ready()
    return engine


def test_scheduler_again_and_good():
    scheduler = StandardFSRSScheduler()
    now = datetime.now(timezone.utc)
    state = LearningStateModel(flashcard_id="fc-1", state=LearningStateEnum.NEW, due_date=now)

    updated_again, review_again = scheduler.schedule(state, ReviewRating.AGAIN, reviewed_at=now)
    assert updated_again.state == LearningStateEnum.RELEARNING
    assert updated_again.repetition == 0
    assert review_again.outcome == "again"

    updated_good, review_good = scheduler.schedule(updated_again, ReviewRating.GOOD, reviewed_at=now)
    assert updated_good.state == LearningStateEnum.REVIEW
    assert updated_good.interval_days >= 1
    assert review_good.outcome == "good"


def test_learning_repository_and_service(temp_db):
    flashcard_repo = SqliteFlashcardRepository(temp_db)
    review_repo = SqliteReviewRepository(temp_db)
    learning_repo = SqliteLearningRepository(temp_db)

    now = datetime.now(timezone.utc)
    source = Source(source_id="src-1", source_type="document", uri="doc-1")
    fc = Flashcard(
        flashcard_id="fc-101",
        front="What is FSRS?",
        back="Free Spaced Repetition Scheduler",
        source=source,
        difficulty=0.3,
        created_at=now,
        updated_at=now,
    )
    flashcard_repo.create_flashcard(fc)

    service = LearningService(
        learning_repo=learning_repo,
        flashcard_repo=flashcard_repo,
        review_repo=review_repo,
    )

    due = service.get_due_reviews()
    assert len(due) == 1
    assert due[0]["flashcard"]["flashcard_id"] == "fc-101"

    res = service.submit_review("fc-101", ReviewRating.GOOD)
    assert res["flashcard_id"] == "fc-101"
    assert res["rating"] == "good"

    stats = service.get_learning_stats()
    assert stats.total_cards == 1
    assert stats.total_reviews == 1
    assert stats.success_rate == 1.0


def test_knowledge_relationships(temp_db):
    learning_repo = SqliteLearningRepository(temp_db)
    now = datetime.now(timezone.utc)
    rel = KnowledgeRelationshipModel(
        relationship_id="rel-1",
        source_id="concept-a",
        target_id="concept-b",
        relation_type=RelationType.PREREQUISITE_OF,
        created_at=now,
    )
    learning_repo.create_knowledge_relationship(rel)

    rels = learning_repo.list_knowledge_relationships("concept-a")
    assert len(rels) == 1
    assert rels[0].relation_type == RelationType.PREREQUISITE_OF


def test_learning_api_endpoints(tmp_path, monkeypatch):
    db_path = tmp_path / "test_api_learning.sqlite3"
    config = DatabaseConfig(path=db_path, timeout_seconds=5.0)
    engine = DatabaseEngine(config)
    engine.ensure_ready()

    from superagent.api import learning as learning_module
    from superagent.application.container import AppContainer

    container = AppContainer(database_engine=engine)
    monkeypatch.setattr(learning_module, "get_container", lambda: container)

    app = create_app()
    client = TestClient(app)

    response = client.post(
        "/api/v1/learning/flashcards",
        json={"front": "What is Python?", "back": "A programming language"},
    )
    assert response.status_code == 200
    data = response.json()
    fc_id = data["flashcard_id"]

    resp_due = client.get("/api/v1/learning/review")
    assert resp_due.status_code == 200
    assert len(resp_due.json()) >= 1

    resp_rev = client.post(
        "/api/v1/learning/review",
        json={"flashcard_id": fc_id, "rating": "easy"},
    )
    assert resp_rev.status_code == 200
    assert resp_rev.json()["rating"] == "easy"

    resp_stats = client.get("/api/v1/learning/stats")
    assert resp_stats.status_code == 200
    assert resp_stats.json()["total_cards"] >= 1
    assert resp_stats.json()["total_reviews"] >= 1

    rel_response = client.post(
        "/api/v1/learning/relationships",
        json={
            "source_id": fc_id,
            "target_id": "concept-python",
            "relation_type": "example_of",
            "metadata": {"confidence": 0.9},
        },
    )
    assert rel_response.status_code == 200
    rel_id = rel_response.json()["relationship_id"]

    listed = client.get(f"/api/v1/learning/relationships/{fc_id}")
    assert listed.status_code == 200
    assert any(item["relationship_id"] == rel_id for item in listed.json())

    self_link = client.post(
        "/api/v1/learning/relationships",
        json={"source_id": fc_id, "target_id": fc_id},
    )
    assert self_link.status_code == 422
