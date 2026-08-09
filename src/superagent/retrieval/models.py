from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field, model_validator


class RetrievalFilter(BaseModel):
    """Filter criteria for candidate retrieval."""

    source_ids: list[str] | None = None
    document_ids: list[str] | None = None
    document_type: str | None = None
    tags: list[str] | None = None
    metadata: dict[str, Any] | None = None


class RerankConfig(BaseModel):
    """Configuration for candidate reranking."""

    enabled: bool = True
    top_n: int | None = Field(default=None, ge=1)
    model_id: str | None = None


class RetrievalQuery(BaseModel):
    """Request model for RAG retrieval with an optional context-token budget."""

    text: str = Field(min_length=1)
    top_k: int = Field(default=10, ge=1)
    candidate_k: int = Field(default=20, ge=1)
    token_budget: int | None = Field(default=None, ge=1)
    filters: RetrievalFilter | None = None
    rerank_config: RerankConfig | None = None

    @model_validator(mode="after")
    def validate_candidate_limit(self) -> "RetrievalQuery":
        if self.candidate_k < self.top_k:
            raise ValueError("candidate_k must be greater than or equal to top_k")
        return self


class RetrievalCandidate(BaseModel):
    """Single document chunk candidate produced by retrieval."""

    chunk_id: str = Field(min_length=1)
    document_id: str = Field(min_length=1)
    version_id: str | None = None
    source_id: str | None = None
    content: str = Field(min_length=1)
    retrieval_method: str = Field(default="hybrid")
    retrieval_score: float = Field(default=0.0)
    dense_score: float | None = None
    lexical_score: float | None = None
    fused_score: float | None = None
    reranker_score: float | None = None
    chunk_index: int = Field(default=0, ge=0)
    metadata: dict[str, Any] = Field(default_factory=dict)
    provenance: dict[str, Any] = Field(default_factory=dict)


class RetrievalResult(BaseModel):
    """Final result of a retrieval query execution."""

    query: str
    candidates: list[RetrievalCandidate] = Field(default_factory=list)
    total_candidates: int = 0
    dense_count: int = 0
    lexical_count: int = 0
    fused_count: int = 0
    reranked: bool = False
    token_budget: int | None = None
    estimated_tokens: int = 0
    duration_ms: float = 0.0
