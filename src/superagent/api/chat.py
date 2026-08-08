from __future__ import annotations

import uuid
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field

from superagent.agents.models import AgentRequest, AgentResponse
from superagent.application.container import AppContainer
from superagent.context.models import ChatMessage

router = APIRouter(tags=["chat"])
_container: AppContainer | None = None


def get_container() -> AppContainer:
    global _container
    if _container is None:
        _container = AppContainer()
    return _container


class ChatRequestPayload(BaseModel):
    message: str = Field(min_length=1)
    conversation_id: str | None = None
    conversation_history: list[ChatMessage] = Field(default_factory=list)
    system_instructions: str | list[str] | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)
    execution_config: dict[str, Any] = Field(default_factory=dict)


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


@router.post("/chat", response_model=ChatResponsePayload)
def chat_endpoint(payload: ChatRequestPayload, container: AppContainer = Depends(get_container)) -> ChatResponsePayload:
    conv_id = payload.conversation_id or f"conv-{uuid.uuid4().hex[:12]}"
    sys_instr = [payload.system_instructions] if isinstance(payload.system_instructions, str) else payload.system_instructions
    response: AgentResponse = container.agent_orchestrator.execute(
        AgentRequest(
            request_id=f"req-{uuid.uuid4().hex[:12]}",
            conversation_id=conv_id,
            message=payload.message,
            conversation_history=payload.conversation_history,
            system_instructions=sys_instr,
            metadata=payload.metadata,
            execution_config=payload.execution_config,
        )
    )
    critique = response.diagnostics.get("critique")
    verification = response.diagnostics.get("verification")
    return ChatResponsePayload(
        answer=response.answer,
        execution_id=response.execution_id,
        conversation_id=response.conversation_id,
        status=response.status.value,
        iterations=response.iterations,
        retrieval_used=response.used_retrieval,
        memory_used=response.used_memory,
        tools_used=response.used_tools,
        critique_status="passed" if critique and critique.get("passed") else "failed" if critique else None,
        verification_status=verification.get("status") if verification else None,
        provenance=response.provenance,
    )


@router.get("/executions/{execution_id}")
def get_execution_endpoint(execution_id: str, container: AppContainer = Depends(get_container)) -> dict[str, Any]:
    state = container.execution_repository.get_execution(execution_id)
    if state is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Execution '{execution_id}' not found.")
    return state.model_dump(mode="json")


@router.get("/executions", response_model=list[dict[str, Any]])
def list_executions_endpoint(container: AppContainer = Depends(get_container)) -> list[dict[str, Any]]:
    return [state.model_dump(mode="json") for state in container.execution_repository.list_executions()]
