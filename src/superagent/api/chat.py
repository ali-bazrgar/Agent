from __future__ import annotations

import base64
import uuid
from typing import Any, Literal

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field, field_validator, model_validator

from superagent.agents.models import AgentRequest, AgentResponse
from superagent.application.container import AppContainer
from superagent.context.models import ChatMessage
from superagent.context.request import Principal
from superagent.api.auth import get_principal

router = APIRouter(tags=["chat"])
_container: AppContainer | None = None
_MAX_ATTACHMENT_BYTES = 12 * 1024 * 1024
_MAX_TOTAL_ATTACHMENT_BYTES = 32 * 1024 * 1024
_MAX_TEXT_ATTACHMENT_BYTES = 2 * 1024 * 1024


def get_container() -> AppContainer:
    global _container
    if _container is None:
        _container = AppContainer()
    return _container


class ChatAttachment(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    mime_type: str = Field(min_length=1, max_length=128)
    kind: Literal["image", "audio", "video", "file"]
    data: str = Field(min_length=1)
    text_content: str | None = None

    @field_validator("data")
    @classmethod
    def validate_data(cls, value: str) -> str:
        raw = value.split(",", 1)[1] if value.startswith("data:") and "," in value else value
        try:
            decoded = base64.b64decode(raw, validate=True)
        except Exception as exc:
            raise ValueError("Attachment data must be valid base64") from exc
        if len(decoded) > _MAX_ATTACHMENT_BYTES:
            raise ValueError("Attachment exceeds the 12 MiB per-file limit")
        return raw

    @field_validator("text_content")
    @classmethod
    def validate_text_content(cls, value: str | None) -> str | None:
        if value is not None and len(value.encode("utf-8")) > _MAX_TEXT_ATTACHMENT_BYTES:
            raise ValueError("Extracted text attachment exceeds the 2 MiB limit")
        return value


class ChatRequestPayload(BaseModel):
    message: str = Field(min_length=1)
    conversation_id: str | None = None
    conversation_history: list[ChatMessage] = Field(default_factory=list)
    system_instructions: str | list[str] | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)
    execution_config: dict[str, Any] = Field(default_factory=dict)
    attachments: list[ChatAttachment] = Field(default_factory=list, max_length=8)

    @model_validator(mode="after")
    def validate_attachment_budget(self) -> "ChatRequestPayload":
        total = sum(len(base64.b64decode(item.data, validate=True)) for item in self.attachments)
        if total > _MAX_TOTAL_ATTACHMENT_BYTES:
            raise ValueError("Total attachments exceed the 32 MiB per-message limit")
        return self


class ChatResponsePayload(BaseModel):
    answer: str
    execution_id: str
    conversation_id: str
    status: str
    iterations: int
    retrieval_used: bool
    memory_used: bool
    tools_used: bool = False
    critique_status: str | None = None
    verification_status: str | None = None
    provenance: list[dict[str, Any]] = Field(default_factory=list)


class ExecutionRequestPayload(BaseModel):
    task_description: str = Field(min_length=1, max_length=20_000)
    conversation_id: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)
    execution_config: dict[str, Any] = Field(default_factory=dict)


def _build_agent_request(message: str, conversation_id: str, principal: Principal, *, request_id: str, conversation_history: list[ChatMessage] | None = None, system_instructions: list[str] | None = None, metadata: dict[str, Any] | None = None, execution_config: dict[str, Any] | None = None) -> AgentRequest:
    return AgentRequest(request_id=request_id, conversation_id=conversation_id, message=message, principal=principal, conversation_history=conversation_history or [], system_instructions=system_instructions, metadata=metadata or {}, execution_config=execution_config or {})


@router.post("/chat", response_model=ChatResponsePayload)
def chat_endpoint(payload: ChatRequestPayload, container: AppContainer = Depends(get_container), principal: Principal = Depends(get_principal)) -> ChatResponsePayload:
    conv_id = payload.conversation_id or f"conv-{uuid.uuid4().hex[:12]}"
    sys_instr = [payload.system_instructions] if isinstance(payload.system_instructions, str) else payload.system_instructions
    metadata = dict(payload.metadata)
    metadata["attachments"] = [item.model_dump(mode="json") for item in payload.attachments]
    response: AgentResponse = container.agent_orchestrator.execute(_build_agent_request(payload.message.strip(), conv_id, principal, request_id=f"req-{uuid.uuid4().hex[:12]}", conversation_history=payload.conversation_history, system_instructions=sys_instr, metadata=metadata, execution_config=payload.execution_config))
    critique = response.diagnostics.get("critique")
    verification = response.diagnostics.get("verification")
    return ChatResponsePayload(answer=response.answer, execution_id=response.execution_id, conversation_id=response.conversation_id, status=response.status.value, iterations=response.iterations, retrieval_used=response.used_retrieval, memory_used=response.used_memory, tools_used=response.used_tools, critique_status="passed" if critique and critique.get("passed") else "failed" if critique else None, verification_status=verification.get("status") if verification else None, provenance=response.provenance)


@router.post("/executions", response_model=dict[str, Any], status_code=status.HTTP_201_CREATED)
def create_execution_endpoint(payload: ExecutionRequestPayload, container: AppContainer = Depends(get_container), principal: Principal = Depends(get_principal)) -> dict[str, Any]:
    conversation_id = payload.conversation_id or f"conv-{uuid.uuid4().hex[:12]}"
    response = container.agent_orchestrator.execute(_build_agent_request(payload.task_description, conversation_id, principal, request_id=f"req-{uuid.uuid4().hex[:12]}", metadata=payload.metadata, execution_config=payload.execution_config))
    execution = container.execution_repository.get_execution(response.execution_id)
    if execution is None:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Execution '{response.execution_id}' was not persisted.")
    payload_out = execution.model_dump(mode="json")
    payload_out["answer"] = response.answer
    payload_out["conversation_id"] = response.conversation_id
    return payload_out


@router.get("/executions/{execution_id}")
def get_execution_endpoint(execution_id: str, container: AppContainer = Depends(get_container)) -> dict[str, Any]:
    state = container.execution_repository.get_execution(execution_id)
    if state is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Execution '{execution_id}' not found.")
    return state.model_dump(mode="json")


@router.get("/executions", response_model=list[dict[str, Any]])
def list_executions_endpoint(container: AppContainer = Depends(get_container)) -> list[dict[str, Any]]:
    return [state.model_dump(mode="json") for state in container.execution_repository.list_executions()]
