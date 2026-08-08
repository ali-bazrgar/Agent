from __future__ import annotations

from datetime import datetime, timezone
from datetime import datetime, timezone
import uuid
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field

from superagent.application.container import AppContainer
from superagent.models.domain import MemoryKind, MemoryStatus, MemoryRecord, Source

router = APIRouter(tags=["memories"])

_container: AppContainer | None = None

def get_container() -> AppContainer:
    global _container
    if _container is None:
        _container = AppContainer()
    return _container

class MemoryRequestPayload(BaseModel):
    kind: MemoryKind = MemoryKind.WORKING
    content: str = Field(min_length=1)
    confidence: float = Field(default=0.9, ge=0.0, le=1.0)
    importance: float = Field(default=0.8, ge=0.0, le=1.0)
    relevance: float = Field(default=0.85, ge=0.0, le=1.0)
    source_title: str | None = None
    provenance: str | None = None

@router.get("/memories", response_model=list[MemoryRecord])
def list_memories(
    kind: MemoryKind | None = None,
    status: MemoryStatus | None = None,
    container: AppContainer = Depends(get_container),
) -> list[MemoryRecord]:
    repo = container.memory_repository
    memories = repo.list_memories()
    
    if kind:
        memories = [m for m in memories if m.kind == kind]
    if status:
        memories = [m for m in memories if m.status == status]
        
    return memories

@router.post("/memories", response_model=MemoryRecord, status_code=status.HTTP_201_CREATED)
def create_memory(
    payload: MemoryRequestPayload,
    container: AppContainer = Depends(get_container),
) -> MemoryRecord:
    repo = container.memory_repository
    
    new_memory = MemoryRecord(
        memory_id=f"mem-{uuid.uuid4().hex[:12]}",
        kind=payload.kind,
        content=payload.content,
        confidence=payload.confidence,
        importance=payload.importance,
        relevance=payload.relevance,
        status=MemoryStatus.ACTIVE,
        source=Source(
            source_id=f"src-{uuid.uuid4().hex[:12]}",
            source_type="user_input",
            title=payload.source_title or "User Ingestion",
        ),
        provenance=payload.provenance,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc)
    )
    
    return repo.create_memory(new_memory)

@router.delete("/memories/{memory_id}")
def delete_memory(
    memory_id: str,
    container: AppContainer = Depends(get_container),
) -> dict[str, Any]:
    # Assuming repository has a delete method, check ports or implement
    # The existing repository might not have delete
    raise HTTPException(status_code=status.HTTP_501_NOT_IMPLEMENTED, detail="Delete not implemented")
