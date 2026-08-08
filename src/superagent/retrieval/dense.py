from __future__ import annotations

import math
from typing import Any

from superagent.core.errors import PersistenceError, ValidationError
from superagent.database.engine import DatabaseEngine
from superagent.retrieval.models import RetrievalCandidate, RetrievalFilter
from superagent.retrieval.ports import DenseRetriever


class SqliteDenseRetriever(DenseRetriever):
    """SQLite vector retrieval implementation computing cosine similarity."""

    def __init__(self, engine: DatabaseEngine) -> None:
        self.engine = engine

    def retrieve_dense(
        self,
        query_vector: list[float],
        top_k: int,
        filters: RetrievalFilter | None = None,
    ) -> list[RetrievalCandidate]:
        if not query_vector:
            raise ValidationError("query_vector cannot be empty")
        if top_k <= 0:
            return []

        try:
            with self.engine.connect() as connection:
                query_sql = """
                    SELECT 
                        e.embedding_id,
                        e.chunk_id,
                        e.document_id,
                        e.version_id,
                        e.dimension,
                        e.vector_json,
                        e.metadata_json AS embedding_metadata_json,
                        kc.content AS kc_content,
                        kc.chunk_index AS kc_chunk_index,
                        kc.metadata_json AS kc_metadata_json,
                        kd.source_id AS kd_source_id,
                        kd.metadata_json AS kd_metadata_json,
                        s.source_type AS s_source_type,
                        s.uri AS s_uri,
                        s.provenance_json AS s_provenance_json,
                        dc.content AS dc_content,
                        dc.chunk_index AS dc_chunk_index,
                        dc.metadata_json AS dc_metadata_json,
                        d.source_type AS d_source_type,
                        d.source_uri AS d_source_uri,
                        d.metadata_json AS d_metadata_json
                    FROM embedding_records e
                    LEFT JOIN knowledge_chunks kc ON e.chunk_id = kc.chunk_id
                    LEFT JOIN knowledge_documents kd ON e.document_id = kd.document_id
                    LEFT JOIN sources s ON kd.source_id = s.source_id
                    LEFT JOIN document_chunks dc ON e.chunk_id = dc.id
                    LEFT JOIN documents d ON e.document_id = d.id
                    WHERE e.chunk_id IS NOT NULL
                """
                params: list[Any] = []

                if filters:
                    if filters.source_ids:
                        placeholders = ",".join("?" for _ in filters.source_ids)
                        query_sql += f" AND (kd.source_id IN ({placeholders}) OR d.id IN ({placeholders}))"
                        params.extend(filters.source_ids)
                        params.extend(filters.source_ids)
                    if filters.document_ids:
                        placeholders = ",".join("?" for _ in filters.document_ids)
                        query_sql += f" AND e.document_id IN ({placeholders})"
                        params.extend(filters.document_ids)
                    if filters.document_type:
                        query_sql += " AND (kd.document_type = ? OR d.source_type = ?)"
                        params.append(filters.document_type)
                        params.append(filters.document_type)

                rows = connection.execute(query_sql, params).fetchall()

        except Exception as exc:  # pragma: no cover
            raise PersistenceError(f"Failed to execute dense retrieval query: {exc}") from exc

        candidates_by_chunk: dict[str, RetrievalCandidate] = {}

        for row in rows:
            dimension = row["dimension"]
            if dimension != len(query_vector):
                raise ValidationError(
                    f"Vector dimension mismatch: query dimension {len(query_vector)} "
                    f"does not match stored dimension {dimension}"
                )

            raw_vector = self.engine.from_json(row["vector_json"])
            if not isinstance(raw_vector, list) or len(raw_vector) != dimension:
                continue

            sim_score = self._cosine_similarity(query_vector, raw_vector)

            chunk_id = row["chunk_id"]
            document_id = row["document_id"]
            version_id = row["version_id"]

            content = row["kc_content"] or row["dc_content"] or ""
            chunk_index = row["kc_chunk_index"] if row["kc_chunk_index"] is not None else (row["dc_chunk_index"] or 0)

            chunk_meta = self.engine.from_json(row["kc_metadata_json"] or row["dc_metadata_json"]) or {}
            doc_meta = self.engine.from_json(row["kd_metadata_json"] or row["d_metadata_json"]) or {}
            combined_meta = {**doc_meta, **chunk_meta}

            source_id = row["kd_source_id"]
            source_type = row["s_source_type"] or row["d_source_type"]
            source_uri = row["s_uri"] or row["d_source_uri"]
            source_provenance = self.engine.from_json(row["s_provenance_json"]) if row["s_provenance_json"] else None

            provenance = {
                "chunk_id": chunk_id,
                "document_id": document_id,
                "version_id": version_id,
                "source_id": source_id,
                "source_type": source_type,
                "source_uri": source_uri,
                "source_provenance": source_provenance,
            }

            candidate = RetrievalCandidate(
                chunk_id=chunk_id,
                document_id=document_id,
                version_id=version_id,
                source_id=source_id,
                content=content,
                retrieval_method="dense",
                retrieval_score=sim_score,
                dense_score=sim_score,
                chunk_index=chunk_index,
                metadata=combined_meta,
                provenance=provenance,
            )

            if chunk_id not in candidates_by_chunk or sim_score > candidates_by_chunk[chunk_id].retrieval_score:
                candidates_by_chunk[chunk_id] = candidate

        candidates = list(candidates_by_chunk.values())
        candidates.sort(key=lambda c: (-c.retrieval_score, c.chunk_id))
        return candidates[:top_k]

    @staticmethod
    def _cosine_similarity(v1: list[float], v2: list[float]) -> float:
        dot = sum(a * b for a, b in zip(v1, v2))
        norm1 = math.sqrt(sum(a * a for a in v1))
        norm2 = math.sqrt(sum(b * b for b in v2))
        if norm1 == 0.0 or norm2 == 0.0:
            return 0.0
        val = dot / (norm1 * norm2)
        return max(-1.0, min(1.0, val))
