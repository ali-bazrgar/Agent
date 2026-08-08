from __future__ import annotations

from datetime import datetime, timezone
from typing import Sequence

from superagent.core.errors import PersistenceError
from superagent.database.engine import DatabaseEngine
from superagent.learning.models import LearningStateModel, LearningStateEnum, KnowledgeRelationshipModel, RelationType, LearningStats


class SqliteLearningRepository:
    """Repository for learning states and knowledge relationships backed by SQLite."""

    def __init__(self, engine: DatabaseEngine) -> None:
        self.engine = engine

    def get_learning_state(self, flashcard_id: str) -> LearningStateModel | None:
        with self.engine.connect() as connection:
            row = connection.execute(
                "SELECT * FROM learning_states WHERE flashcard_id = ?",
                (flashcard_id,),
            ).fetchone()
        if not row:
            return None
        return self._state_from_row(row)

    def save_learning_state(self, state: LearningStateModel) -> LearningStateModel:
        try:
            with self.engine.connect() as connection:
                connection.execute(
                    """
                    INSERT OR REPLACE INTO learning_states 
                    (flashcard_id, state, due_date, interval_days, repetition, ease_factor, stability, difficulty, last_reviewed_at, created_at, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        state.flashcard_id,
                        state.state.value,
                        state.due_date.isoformat(),
                        state.interval_days,
                        state.repetition,
                        state.ease_factor,
                        state.stability,
                        state.difficulty,
                        state.last_reviewed_at.isoformat() if state.last_reviewed_at else None,
                        state.created_at.isoformat(),
                        state.updated_at.isoformat(),
                    ),
                )
                connection.commit()
        except Exception as exc:
            raise PersistenceError(f"failed to save learning state: {exc}") from exc
        return state

    def list_learning_states(self) -> Sequence[LearningStateModel]:
        with self.engine.connect() as connection:
            rows = connection.execute("SELECT * FROM learning_states").fetchall()
        return [self._state_from_row(row) for row in rows]

    def list_due_learning_states(self, now: datetime, limit: int = 50) -> Sequence[LearningStateModel]:
        with self.engine.connect() as connection:
            rows = connection.execute(
                "SELECT * FROM learning_states WHERE due_date <= ? ORDER BY due_date ASC LIMIT ?",
                (now.isoformat(), limit),
            ).fetchall()
        return [self._state_from_row(row) for row in rows]

    def create_knowledge_relationship(self, rel: KnowledgeRelationshipModel) -> KnowledgeRelationshipModel:
        try:
            with self.engine.connect() as connection:
                connection.execute(
                    """
                    INSERT INTO knowledge_relationships (relationship_id, source_id, target_id, relation_type, metadata_json, created_at)
                    VALUES (?, ?, ?, ?, ?, ?)
                    """,
                    (
                        rel.relationship_id,
                        rel.source_id,
                        rel.target_id,
                        rel.relation_type.value,
                        DatabaseEngine.to_json(rel.metadata),
                        rel.created_at.isoformat(),
                    ),
                )
                connection.commit()
        except Exception as exc:
            raise PersistenceError(f"failed to create knowledge relationship: {exc}") from exc
        return rel

    def list_knowledge_relationships(self, source_id: str) -> Sequence[KnowledgeRelationshipModel]:
        with self.engine.connect() as connection:
            rows = connection.execute(
                "SELECT * FROM knowledge_relationships WHERE source_id = ? OR target_id = ?",
                (source_id, source_id),
            ).fetchall()
        return [self._rel_from_row(row) for row in rows]

    def _state_from_row(self, row: object) -> LearningStateModel:
        return LearningStateModel(
            flashcard_id=row["flashcard_id"],
            state=LearningStateEnum(row["state"]),
            due_date=datetime.fromisoformat(row["due_date"]),
            interval_days=row["interval_days"],
            repetition=row["repetition"],
            ease_factor=row["ease_factor"],
            stability=row["stability"],
            difficulty=row["difficulty"],
            last_reviewed_at=datetime.fromisoformat(row["last_reviewed_at"]) if row["last_reviewed_at"] else None,
            created_at=datetime.fromisoformat(row["created_at"]),
            updated_at=datetime.fromisoformat(row["updated_at"]),
        )

    def _rel_from_row(self, row: object) -> KnowledgeRelationshipModel:
        return KnowledgeRelationshipModel(
            relationship_id=row["relationship_id"],
            source_id=row["source_id"],
            target_id=row["target_id"],
            relation_type=RelationType(row["relation_type"]),
            metadata=DatabaseEngine.from_json(row["metadata_json"]) or {},
            created_at=datetime.fromisoformat(row["created_at"]),
        )
