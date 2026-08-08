from __future__ import annotations

from typing import Sequence

from superagent.core.errors import PersistenceError
from superagent.database.engine import DatabaseEngine
from superagent.models.domain import Source
from superagent.repositories.ports import SourceRepository


class SqliteSourceRepository(SourceRepository):
    def __init__(self, engine: DatabaseEngine) -> None:
        self.engine = engine

    def create_source(self, source: Source) -> Source:
        try:
            with self.engine.connect() as connection:
                connection.execute(
                    """
                    INSERT INTO sources (
                        source_id, source_type, uri, locator, title, content_hash,
                        metadata_json, provenance_json, created_at, updated_at
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        source.source_id,
                        source.source_type,
                        source.uri,
                        source.locator,
                        source.title,
                        source.content_hash,
                        self.engine.to_json(source.metadata),
                        self.engine.to_json(source.provenance),
                        source.created_at.isoformat(),
                        source.updated_at.isoformat(),
                    ),
                )
                connection.commit()
        except Exception as exc:  # pragma: no cover - defensive branch
            raise PersistenceError(f"failed to create source: {exc}") from exc
        return source

    def get_source(self, source_id: str) -> Source | None:
        with self.engine.connect() as connection:
            row = connection.execute(
                "SELECT * FROM sources WHERE source_id = ?",
                (source_id,),
            ).fetchone()
        if row is None:
            return None
        return self._from_row(row)

    def get_source_by_content_hash(self, content_hash: str) -> Source | None:
        if not content_hash:
            return None
        with self.engine.connect() as connection:
            row = connection.execute(
                "SELECT * FROM sources WHERE content_hash = ?",
                (content_hash,),
            ).fetchone()
        if row is None:
            return None
        return self._from_row(row)

    def list_sources(self) -> Sequence[Source]:
        with self.engine.connect() as connection:
            rows = connection.execute("SELECT * FROM sources ORDER BY created_at").fetchall()
        return [self._from_row(row) for row in rows]

    def _from_row(self, row: object) -> Source:
        from datetime import datetime

        return Source(
            source_id=row["source_id"],
            source_type=row["source_type"],
            uri=row["uri"],
            locator=row["locator"],
            title=row["title"],
            content_hash=row["content_hash"],
            metadata=self.engine.from_json(row["metadata_json"]) or {},
            provenance=self.engine.from_json(row["provenance_json"]),
            created_at=datetime.fromisoformat(row["created_at"]),
            updated_at=datetime.fromisoformat(row["updated_at"]),
        )
