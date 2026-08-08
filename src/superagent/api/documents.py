from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field

from superagent.application.container import AppContainer
from superagent.core.errors import ProviderError, ValidationError
from superagent.knowledge.ingest.pipeline import IngestionRequest
from superagent.models.domain import Document
from superagent.api.chat import get_container

router = APIRouter(tags=["documents"])


class DocumentRequestPayload(BaseModel):
    title: str = Field(min_length=1)
    content: str = Field(min_length=1)
    source_uri: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


@router.get("/documents", response_model=list[Document])
def list_documents(
    container: AppContainer = Depends(get_container),
) -> list[Document]:
    return list(container.document_repository.list_documents())


@router.post("/documents", response_model=Document, status_code=status.HTTP_201_CREATED)
def create_document(
    payload: DocumentRequestPayload,
    container: AppContainer = Depends(get_container),
) -> Document:
    """Ingest a document through the canonical knowledge pipeline.

    This endpoint deliberately does not bypass chunking/embedding/versioning:
    a successful document creation therefore produces a queryable knowledge
    record rather than only a row in the legacy document index.
    """
    try:
        result = container.ingestion_pipeline.ingest(
            IngestionRequest(
                title=payload.title.strip(),
                content=payload.content,
                source_type="user_upload",
                uri=payload.source_uri,
                content_type="text/plain",
                metadata=payload.metadata,
                provenance={"created_via": "api"},
            )
        )
    except (ValidationError, ProviderError) as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc
    return result.document
