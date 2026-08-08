from __future__ import annotations

from typing import Sequence

from superagent.core.errors import PersistenceError
from superagent.database.engine import DatabaseEngine
from superagent.models.domain import EmbeddingRecord
from superagent.repositories.ports import EmbeddingRepository


class SqliteEmbeddingRepository(EmbeddingRepository):
    def __init__(self, engine: DatabaseEngine) -> None:
        self.engine = engine

    def create_embedding(self, embedding: EmbeddingRecord) -> EmbeddingRecord:
        try:
            with self.engine.connect() as connection:
                connection.execute(
                    """
                    INSERT INTO embedding_records (
                        embedding_id, chunk_id, document_id, version_id, model_id,
                        dimension, vector_json, content_hash, metadata_json, created_at, updated_at
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        embedding.embedding_id,
                        embedding.chunk_id,
                        embedding.document_id,
                        embedding.version_id,
                        embedding.model_id,
                        embedding.dimension,
                        embedding.vector_json,
                        embedding.content_hash,
                        self.engine.to_json(embedding.metadata),
                        embedding.created_at.isoformat(),
                        embedding.updated_at.isoformat(),
                    ),
                )
                connection.commit()
        except Exception as exc:  # pragma: no cover - defensive branch
            raise PersistenceError(f"failed to create embedding record: {exc}") from exc
        return embedding

    def get_embedding(self, embedding_id: str) -> EmbeddingRecord | None:
        with self.engine.connect() as connection:
            row = connection.execute(
                "SELECT * FROM embedding_records WHERE embedding_id = ?",
                (embedding_id,),
            ).fetchone()
        if row is None:
            return None
        return self._from_row(row)

    def list_embeddings_for_chunk(self, chunk_id: str) -> Sequence[EmbeddingRecord]:
        with self.engine.connect() as connection:
            rows = connection.execute(
                "SELECT * FROM embedding_records WHERE chunk_id = ? ORDER BY created_at",
                (chunk_id,),
            ).fetchall()
        return [self._from_row(row) for row in rows]

    def _from_row(self, row: object) -> EmbeddingRecord:
        from datetime import datetime

        return EmbeddingRecord(
            embedding_id=row["embedding_id"],
            chunk_id=row["chunk_id"],
            document_id=row["document_id"],
            version_id=row["version_id"],
            model_id=row["model_id"],
            dimension=row["dimension"],
            vector_json=row["vector_json"],
            content_hash=row["content_hash"],
            metadata=self.engine.from_json(row["metadata_json"]) or {},
            created_at=datetime.fromisoformat(row["created_at"]),
            updated_at=datetime.fromisoformat(row["updated_at"]),
        )
