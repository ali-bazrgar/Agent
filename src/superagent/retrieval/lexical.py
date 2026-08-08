from __future__ import annotations

import re
from typing import Any

from superagent.core.errors import PersistenceError
from superagent.database.engine import DatabaseEngine
from superagent.retrieval.models import RetrievalCandidate, RetrievalFilter
from superagent.retrieval.ports import LexicalRetriever


class SqliteLexicalRetriever(LexicalRetriever):
    """SQLite FTS5 full-text lexical search retriever."""

    def __init__(self, engine: DatabaseEngine) -> None:
        self.engine = engine

    def retrieve_lexical(
        self,
        query_text: str,
        top_k: int,
        filters: RetrievalFilter | None = None,
    ) -> list[RetrievalCandidate]:
        if not query_text or not query_text.strip():
            return []
        if top_k <= 0:
            return []

        terms = re.findall(r"\w+", query_text)
        if not terms:
            return []

        # Form FTS match query with escaped term quotes
        fts_query = " OR ".join(f'"{term}"' for term in terms)

        try:
            with self.engine.connect() as connection:
                self._ensure_fts_synced(connection)

                sql = """
                    SELECT 
                        fts.chunk_id,
                        fts.content,
                        bm25(chunk_search_fts) AS bm25_rank,
                        kc.document_id AS kc_doc_id,
                        kc.version_id AS kc_ver_id,
                        kc.chunk_index AS kc_chunk_index,
                        kc.metadata_json AS kc_metadata_json,
                        kd.source_id AS kd_source_id,
                        kd.metadata_json AS kd_metadata_json,
                        s.source_type AS s_source_type,
                        s.uri AS s_uri,
                        s.provenance_json AS s_provenance_json,
                        dc.document_id AS dc_doc_id,
                        dc.chunk_index AS dc_chunk_index,
                        dc.metadata_json AS dc_metadata_json,
                        d.source_type AS d_source_type,
                        d.source_uri AS d_source_uri,
                        d.metadata_json AS d_metadata_json
                    FROM chunk_search_fts fts
                    LEFT JOIN knowledge_chunks kc ON fts.chunk_id = kc.chunk_id
                    LEFT JOIN knowledge_documents kd ON kc.document_id = kd.document_id
                    LEFT JOIN sources s ON kd.source_id = s.source_id
                    LEFT JOIN document_chunks dc ON fts.chunk_id = dc.id
                    LEFT JOIN documents d ON dc.document_id = d.id
                    WHERE chunk_search_fts MATCH ?
                """
                params: list[Any] = [fts_query]

                if filters:
                    if filters.source_ids:
                        placeholders = ",".join("?" for _ in filters.source_ids)
                        sql += f" AND (kd.source_id IN ({placeholders}) OR d.id IN ({placeholders}))"
                        params.extend(filters.source_ids)
                        params.extend(filters.source_ids)
                    if filters.document_ids:
                        placeholders = ",".join("?" for _ in filters.document_ids)
                        sql += f" AND (kc.document_id IN ({placeholders}) OR dc.document_id IN ({placeholders}))"
                        params.extend(filters.document_ids)
                        params.extend(filters.document_ids)
                    if filters.document_type:
                        sql += " AND (kd.document_type = ? OR d.source_type = ?)"
                        params.append(filters.document_type)
                        params.append(filters.document_type)

                sql += " ORDER BY bm25_rank ASC LIMIT ?"
                params.append(top_k)

                rows = connection.execute(sql, params).fetchall()

        except Exception as exc:  # pragma: no cover
            raise PersistenceError(f"Failed to execute lexical search query: {exc}") from exc

        candidates: list[RetrievalCandidate] = []
        for row in rows:
            chunk_id = row["chunk_id"]
            content = row["content"]
            rank = row["bm25_rank"]
            # Convert negative BM25 rank to positive score
            lexical_score = -float(rank) if rank is not None else 0.0

            document_id = row["kc_doc_id"] or row["dc_doc_id"] or ""
            version_id = row["kc_ver_id"]
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
                retrieval_method="lexical",
                retrieval_score=lexical_score,
                lexical_score=lexical_score,
                chunk_index=chunk_index,
                metadata=combined_meta,
                provenance=provenance,
            )
            candidates.append(candidate)

        candidates.sort(key=lambda c: (-c.retrieval_score, c.chunk_id))
        return candidates[:top_k]

    def _ensure_fts_synced(self, connection: Any) -> None:
        """Sync chunks into chunk_search_fts if missing."""
        try:
            # Sync from knowledge_chunks
            connection.execute(
                """
                INSERT INTO chunk_search_fts (chunk_id, content)
                SELECT kc.chunk_id, kc.content
                FROM knowledge_chunks kc
                LEFT JOIN chunk_search_fts fts ON kc.chunk_id = fts.chunk_id
                WHERE fts.chunk_id IS NULL
                """
            )
            # Sync from document_chunks
            connection.execute(
                """
                INSERT INTO chunk_search_fts (chunk_id, content)
                SELECT dc.id, dc.content
                FROM document_chunks dc
                LEFT JOIN chunk_search_fts fts ON dc.id = fts.chunk_id
                WHERE fts.chunk_id IS NULL
                """
            )
            connection.commit()
        except Exception:  # pragma: no cover - defensive table setup
            pass
