from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field

from superagent.application.container import AppContainer
from superagent.api.chat import get_container
from superagent.models.domain import MemoryKind, MemoryStatus, MemoryRecord, Source

router = APIRouter(tags=["memories"])


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
    memories = list(container.memory_repository.list_memories())
    if kind:
        memories = [memory for memory in memories if memory.kind == kind]
    if status:
        memories = [memory for memory in memories if memory.status == status]
    return memories


@router.post("/memories", response_model=MemoryRecord, status_code=status.HTTP_201_CREATED)
def create_memory(
    payload: MemoryRequestPayload,
    container: AppContainer = Depends(get_container),
) -> MemoryRecord:
    now = datetime.now(timezone.utc)
    new_memory = MemoryRecord(
        memory_id=f"mem-{uuid.uuid4().hex[:12]}",
        kind=payload.kind,
        content=payload.content.strip(),
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
        created_at=now,
        updated_at=now,
    )
    return container.memory_repository.create_memory(new_memory)


@router.delete("/memories/{memory_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_memory(
    memory_id: str,
    container: AppContainer = Depends(get_container),
) -> None:
    if container.memory_repository.get_memory(memory_id) is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Memory '{memory_id}' not found.")
    container.memory_repository.update_status(memory_id, MemoryStatus.DELETED.value)
