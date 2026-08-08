from __future__ import annotations

import uuid
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from datetime import datetime, timezone

from superagent.application.container import AppContainer
from superagent.models.domain import Document, Source

router = APIRouter(tags=["documents"])

_container: AppContainer | None = None

def get_container() -> AppContainer:
    global _container
    if _container is None:
        _container = AppContainer()
    return _container

class DocumentRequestPayload(BaseModel):
    title: str = Field(min_length=1)
    content: str = Field(min_length=1)
    source_uri: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)

@router.get("/documents", response_model=list[Document])
def list_documents(
    container: AppContainer = Depends(get_container),
) -> list[Document]:
    repo = container.document_repository
    return list(repo.list_documents())

@router.post("/documents", response_model=Document, status_code=status.HTTP_201_CREATED)
def create_document(
    payload: DocumentRequestPayload,
    container: AppContainer = Depends(get_container),
) -> Document:
    repo = container.document_repository
    
    new_doc = Document(
        document_id=f"doc-{uuid.uuid4().hex[:12]}",
        title=payload.title,
        source=Source(
            source_id=f"src-{uuid.uuid4().hex[:12]}",
            source_type="user_upload",
            uri=payload.source_uri,
        ),
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc)
    )
    
    return repo.create_document(new_doc)
