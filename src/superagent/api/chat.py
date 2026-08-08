from __future__ import annotations

import uuid
from typing import Any, Sequence

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field

from superagent.agents.models import AgentRequest, AgentResponse
from superagent.application.container import AppContainer

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
    system_instructions: str | list[str] | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)
    execution_config: dict[str, Any] = Field(default_factory=dict)


class ChatResponsePayload(BaseModel):
    answer: str
    execution_id: str
    status: str
    iterations: int
    retrieval_used: bool
    memory_used: bool
    critique_status: str | None = None
    verification_status: str | None = None
    provenance: list[dict[str, Any]] = Field(default_factory=list)


@router.post("/chat", response_model=ChatResponsePayload)
def chat_endpoint(
    payload: ChatRequestPayload,
    container: AppContainer = Depends(get_container),
) -> ChatResponsePayload:
    orchestrator = container.agent_orchestrator

    req_id = f"req-{uuid.uuid4().hex[:12]}"
    conv_id = payload.conversation_id or f"conv-{uuid.uuid4().hex[:12]}"

    sys_instr: list[str] | None = None
    if isinstance(payload.system_instructions, str):
        sys_instr = [payload.system_instructions]
    elif isinstance(payload.system_instructions, list):
        sys_instr = payload.system_instructions

    agent_request = AgentRequest(
        request_id=req_id,
        conversation_id=conv_id,
        message=payload.message,
        system_instructions=sys_instr,
        metadata=payload.metadata,
        execution_config=payload.execution_config,
    )

    response: AgentResponse = orchestrator.execute(agent_request)

    critique_diag = response.diagnostics.get("critique")
    critique_status = "passed" if (critique_diag and critique_diag.get("passed")) else "failed" if critique_diag else None

    verif_diag = response.diagnostics.get("verification")
    verif_status = verif_diag.get("status") if verif_diag else None

    return ChatResponsePayload(
        answer=response.answer,
        execution_id=response.execution_id,
        status=response.status.value,
        iterations=response.iterations,
        retrieval_used=response.used_retrieval,
        memory_used=response.used_memory,
        critique_status=critique_status,
        verification_status=verif_status,
        provenance=response.provenance,
    )


@router.get("/executions/{execution_id}")
def get_execution_endpoint(
    execution_id: str,
    container: AppContainer = Depends(get_container),
) -> dict[str, Any]:
    exec_repo = container.execution_repository
    state = exec_repo.get_execution(execution_id)

    if state is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Execution '{execution_id}' not found.",
        )

    return state.model_dump(mode="json")


@router.get("/executions", response_model=list[dict[str, Any]])
def list_executions_endpoint(
    container: AppContainer = Depends(get_container),
) -> list[dict[str, Any]]:
    exec_repo = container.execution_repository
    executions = exec_repo.list_executions()

    return [e.model_dump(mode="json") for e in executions]
