from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field

from superagent.api.chat import get_container
from superagent.application.container import AppContainer
from superagent.core.errors import ProviderError, ValidationError
from superagent.knowledge.ingest.pipeline import IngestionRequest
from superagent.models.domain import Document

router = APIRouter(tags=["documents"])


class DocumentRequestPayload(BaseModel):
    title: str = Field(min_length=1)
    content: str = Field(min_length=1)
    source_uri: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


@router.get("/documents", response_model=list[Document])
def list_documents(container: AppContainer = Depends(get_container)) -> list[Document]:
    return list(container.document_repository.list_documents())


@router.post("/documents", response_model=Document, status_code=status.HTTP_201_CREATED)
def create_document(
    payload: DocumentRequestPayload,
    container: AppContainer = Depends(get_container),
) -> Document:
    """Ingest a document through the canonical chunk/embed/version pipeline."""
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


@router.delete("/documents/{document_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_document(
    document_id: str,
    container: AppContainer = Depends(get_container),
) -> None:
    if not container.document_repository.delete_document(document_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Document '{document_id}' not found.")
