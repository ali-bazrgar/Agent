from __future__ import annotations

from typing import Sequence

from superagent.core.errors import PersistenceError
from superagent.database.engine import DatabaseEngine
from superagent.models.domain import Tag
from superagent.repositories.ports import TagRepository


class SqliteTagRepository(TagRepository):
    def __init__(self, engine: DatabaseEngine) -> None:
        self.engine = engine

    def add_tag(self, tag: Tag) -> Tag:
        try:
            with self.engine.connect() as connection:
                connection.execute(
                    """
                    INSERT INTO tags (
                        tag_id, resource_type, resource_id, name, value, created_at
                    )
                    VALUES (?, ?, ?, ?, ?, ?)
                    """,
                    (
                        tag.tag_id,
                        tag.resource_type,
                        tag.resource_id,
                        tag.name,
                        tag.value,
                        tag.created_at.isoformat(),
                    ),
                )
                connection.commit()
        except Exception as exc:  # pragma: no cover - defensive branch
            raise PersistenceError(f"failed to add tag: {exc}") from exc
        return tag

    def list_tags(self, resource_type: str, resource_id: str) -> Sequence[Tag]:
        with self.engine.connect() as connection:
            rows = connection.execute(
                "SELECT * FROM tags WHERE resource_type = ? AND resource_id = ? ORDER BY created_at",
                (resource_type, resource_id),
            ).fetchall()
        return [self._from_row(row) for row in rows]

    def _from_row(self, row: object) -> Tag:
        from datetime import datetime

        return Tag(
            tag_id=row["tag_id"],
            resource_type=row["resource_type"],
            resource_id=row["resource_id"],
            name=row["name"],
            value=row["value"],
            created_at=datetime.fromisoformat(row["created_at"]),
        )
