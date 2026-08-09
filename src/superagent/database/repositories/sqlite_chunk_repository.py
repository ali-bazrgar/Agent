from __future__ import annotations

import uuid
from typing import Sequence

from superagent.core.errors import PersistenceError
from superagent.database.engine import DatabaseEngine
from superagent.models.domain import DocumentChunk
from superagent.repositories.ports import ChunkRepository


class SqliteChunkRepository(ChunkRepository):
    def __init__(self, engine: DatabaseEngine) -> None:
        self.engine = engine

    def create_chunk(self, chunk: DocumentChunk) -> DocumentChunk:
        try:
            with self.engine.connect() as connection:
                connection.execute(
                    """
                    INSERT INTO document_chunks (id, document_id, content, chunk_index, token_count, metadata_json, created_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        chunk.chunk_id, chunk.document_id, chunk.content, chunk.chunk_index,
                        chunk.token_count, self.engine.to_json(chunk.metadata), chunk.created_at.isoformat(),
                    ),
                )
                connection.execute(
                    """
                    INSERT INTO knowledge_chunks (
                        chunk_id, document_id, version_id, content, content_hash, chunk_index,
                        token_count, character_count, language, metadata_json, created_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        chunk.chunk_id, chunk.document_id, chunk.version_id, chunk.content,
                        chunk.content_hash, chunk.chunk_index, chunk.token_count,
                        chunk.character_count or len(chunk.content), chunk.language,
                        self.engine.to_json(chunk.metadata), chunk.created_at.isoformat(),
                    ),
                )
                connection.execute(
                    "INSERT INTO chunk_search_fts (chunk_id, content) VALUES (?, ?)",
                    (chunk.chunk_id, chunk.content),
                )
                connection.execute(
                    """
                    INSERT INTO lexical_index_entries (entry_id, chunk_id, content, created_at)
                    VALUES (?, ?, ?, ?)
                    """,
                    (f"lex-{uuid.uuid4().hex[:12]}", chunk.chunk_id, chunk.content, chunk.created_at.isoformat()),
                )
                connection.commit()
        except Exception as exc:
            raise PersistenceError(f"failed to create chunk and indexes: {exc}") from exc
        return chunk

    def list_chunks_for_document(self, document_id: str) -> Sequence[DocumentChunk]:
        with self.engine.connect() as connection:
            rows = connection.execute(
                "SELECT * FROM knowledge_chunks WHERE document_id = ? ORDER BY chunk_index", (document_id,)
            ).fetchall()
            if rows:
                return [self._from_knowledge_chunk_row(row) for row in rows]
            rows = connection.execute(
                "SELECT * FROM document_chunks WHERE document_id = ? ORDER BY chunk_index", (document_id,)
            ).fetchall()
        return [self._from_row(row) for row in rows]

    def get_chunk(self, chunk_id: str) -> DocumentChunk | None:
        with self.engine.connect() as connection:
            row = connection.execute("SELECT * FROM knowledge_chunks WHERE chunk_id = ?", (chunk_id,)).fetchone()
            if row is not None:
                return self._from_knowledge_chunk_row(row)
            row = connection.execute("SELECT * FROM document_chunks WHERE id = ?", (chunk_id,)).fetchone()
            return self._from_row(row) if row is not None else None

    def _from_knowledge_chunk_row(self, row: object) -> DocumentChunk:
        from datetime import datetime

        return DocumentChunk(
            chunk_id=row["chunk_id"], document_id=row["document_id"], version_id=row["version_id"],
            content=row["content"], content_hash=row["content_hash"], chunk_index=row["chunk_index"],
            token_count=row["token_count"], character_count=row["character_count"], language=row["language"],
            metadata=self.engine.from_json(row["metadata_json"]) or {},
            created_at=datetime.fromisoformat(row["created_at"]),
        )

    def _from_row(self, row: object) -> DocumentChunk:
        from datetime import datetime

        return DocumentChunk(
            chunk_id=row["id"], document_id=row["document_id"], content=row["content"],
            chunk_index=row["chunk_index"], token_count=row["token_count"],
            metadata=self.engine.from_json(row["metadata_json"]) or {},
            created_at=datetime.fromisoformat(row["created_at"]),
        )
