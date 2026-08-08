from __future__ import annotations

from typing import Sequence

from superagent.core.errors import PersistenceError
from superagent.database.engine import DatabaseEngine
from superagent.models.domain import Flashcard, Source
from superagent.repositories.ports import FlashcardRepository


class SqliteFlashcardRepository(FlashcardRepository):
    def __init__(self, engine: DatabaseEngine) -> None:
        self.engine = engine

    def create_flashcard(self, flashcard: Flashcard) -> Flashcard:
        try:
            with self.engine.connect() as connection:
                connection.execute(
                    """
                    INSERT INTO flashcards (id, front, back, source_type, source_uri, difficulty, created_at, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        flashcard.flashcard_id,
                        flashcard.front,
                        flashcard.back,
                        flashcard.source.source_type if flashcard.source else None,
                        flashcard.source.uri if flashcard.source else None,
                        flashcard.difficulty,
                        flashcard.created_at.isoformat(),
                        flashcard.updated_at.isoformat(),
                    ),
                )
                connection.commit()
        except Exception as exc:  # pragma: no cover - defensive branch
            raise PersistenceError(f"failed to create flashcard: {exc}") from exc
        return flashcard

    def get_flashcard(self, flashcard_id: str) -> Flashcard | None:
        with self.engine.connect() as connection:
            row = connection.execute("SELECT * FROM flashcards WHERE id = ?", (flashcard_id,)).fetchone()
        if row is None:
            return None
        return self._from_row(row)

    def list_flashcards(self) -> Sequence[Flashcard]:
        with self.engine.connect() as connection:
            rows = connection.execute("SELECT * FROM flashcards ORDER BY created_at").fetchall()
        return [self._from_row(row) for row in rows]

    def _from_row(self, row: object) -> Flashcard:
        from datetime import datetime

        return Flashcard(
            flashcard_id=row["id"],
            front=row["front"],
            back=row["back"],
            source=Source(source_id=row["id"], source_type=row["source_type"] or "unknown", uri=row["source_uri"]),
            difficulty=row["difficulty"],
            created_at=datetime.fromisoformat(row["created_at"]),
            updated_at=datetime.fromisoformat(row["updated_at"]),
        )
