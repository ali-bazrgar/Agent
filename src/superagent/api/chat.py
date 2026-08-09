from __future__ import annotations

import base64
import uuid
from typing import Any, Literal

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel, Field, field_validator, model_validator

from superagent.agents.models import AgentRequest, AgentResponse
from superagent.application.container import AppContainer
from superagent.context.models import ChatMessage

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


class ChatRuntimeOptions(BaseModel):
    context_window: int | None = Field(default=None, ge=256)
    memory_recall: bool | None = None
    knowledge_retrieval: bool | None = None
    conversation_history_max_messages: int | None = Field(default=8, ge=0)
    reasoning_mode: Literal["auto", "on", "off"] = "auto"


class ChatRequestPayload(BaseModel):
    message: str = Field(min_length=1)
    conversation_id: str | None = None
    conversation_history: list[ChatMessage] = Field(default_factory=list)
    system_instructions: str | list[str] | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)
    execution_config: dict[str, Any] = Field(default_factory=dict)
    runtime_options: ChatRuntimeOptions | None = None
    attachments: list[ChatAttachment] = Field(default_factory=list, max_length=8)

    @model_validator(mode="after")
    def validate_attachment_budget(self) -> "ChatRequestPayload":
        total = sum(len(base64.b64decode(item.data, validate=True)) for item in self.attachments)
        if total > _MAX_TOTAL_ATTACHMENT_BYTES:
            raise ValueError("Total attachments exceed the 32 MiB per-message limit")
        return self

    def resolved_execution_config(self) -> dict[str, Any]:
        config = dict(self.execution_config)
        if self.runtime_options is None:
            config["conversation_history_max_messages"] = config.get("conversation_history_max_messages", 8)
            config["reasoning_mode"] = config.get("reasoning_mode", "auto")
            return config
        options = self.runtime_options
        if options.context_window is not None:
            config["context_window_tokens"] = options.context_window
        if options.memory_recall is not None:
            config["memory_recall_every_message"] = options.memory_recall
        if options.knowledge_retrieval is not None:
            config["knowledge_retrieval_enabled"] = options.knowledge_retrieval
        if options.conversation_history_max_messages is not None:
            config["conversation_history_max_messages"] = options.conversation_history_max_messages
        config["reasoning_mode"] = options.reasoning_mode
        return config


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
    telemetry: dict[str, Any] = Field(default_factory=dict)
    request_id: str | None = None


class ExecutionRequestPayload(BaseModel):
    task_description: str = Field(min_length=1, max_length=20_000)
    conversation_id: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)
    execution_config: dict[str, Any] = Field(default_factory=dict)


def _build_telemetry(response: AgentResponse, context_window: int | None = None) -> dict[str, Any]:
    diagnostics = response.diagnostics if isinstance(response.diagnostics, dict) else {}
    context = diagnostics.get("context") if isinstance(diagnostics.get("context"), dict) else {}
    usage = diagnostics.get("llm_usage") if isinstance(diagnostics.get("llm_usage"), dict) else {}
    timings = diagnostics.get("llm_timings") if isinstance(diagnostics.get("llm_timings"), dict) else {}
    memory = diagnostics.get("memory_recall") if isinstance(diagnostics.get("memory_recall"), dict) else {}
    knowledge = diagnostics.get("knowledge_retrieval") if isinstance(diagnostics.get("knowledge_retrieval"), dict) else {}
    return {
        "context_window": context.get("context_window", context_window),
        "prompt_tokens": usage.get("prompt_tokens", timings.get("prompt_n")),
        "output_tokens": usage.get("completion_tokens", usage.get("output_tokens", timings.get("predicted_n"))),
        "total_tokens": usage.get("total_tokens"),
        "prompt_tokens_estimated": context.get("prompt_tokens_estimated"),
        "prompt_tps": timings.get("prompt_per_second"),
        "generation_tps": timings.get("predicted_per_second"),
        "prompt_ms": timings.get("prompt_ms"),
        "generation_ms": timings.get("predicted_ms"),
        "memory_matches": memory.get("matches", 0),
        "memory_tokens": context.get("allocated_tokens", {}).get("memory", 0) if isinstance(context.get("allocated_tokens"), dict) else 0,
        "knowledge_candidates": knowledge.get("candidates", 0),
        "knowledge_tokens": context.get("allocated_tokens", {}).get("knowledge", 0) if isinstance(context.get("allocated_tokens"), dict) else 0,
        "selected_context_tokens": context.get("selected_tokens", 0),
    }


def _validate_attachment_capabilities(container: AppContainer, attachments: list[ChatAttachment]) -> None:
    if not attachments:
        return
    capabilities = container.llm_provider.capabilities()
    unsupported: list[str] = []
    if any(item.kind == "image" for item in attachments) and not capabilities.vision:
        unsupported.append("image")
    if any(item.kind == "audio" for item in attachments) and not capabilities.audio_input:
        unsupported.append("audio")
    if any(item.kind == "video" for item in attachments) and not capabilities.video_input:
        unsupported.append("video")
    if unsupported:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=f"The active LLM provider does not advertise support for: {', '.join(unsupported)}.")


def _prepare_chat_request(payload: ChatRequestPayload, request: Request, container: AppContainer) -> tuple[AgentRequest, dict[str, Any], str]:
    _validate_attachment_capabilities(container, payload.attachments)
    conv_id = payload.conversation_id or f"conv-{uuid.uuid4().hex[:12]}"
    request_id = request.headers.get("x-request-id") or f"req-{uuid.uuid4().hex[:12]}"
    sys_instr = [payload.system_instructions] if isinstance(payload.system_instructions, str) else payload.system_instructions
    metadata = dict(payload.metadata)
    metadata["attachments"] = [item.model_dump(mode="json") for item in payload.attachments]
    config = payload.resolved_execution_config()
    config.setdefault("max_execution_time_seconds", int(container.runtime_config.timeout_seconds) if container.runtime_config is not None else 600)
    if container.runtime_config is not None:
        config.setdefault("context_allocation", container.runtime_config.context_allocation.model_dump(mode="json"))
    metadata["_conversation_history_max_messages"] = config.get("conversation_history_max_messages", 8)
    metadata["reasoning_mode"] = config.get("reasoning_mode", "auto")
    if isinstance(config.get("context_allocation"), dict):
        metadata["_context_allocation"] = dict(config["context_allocation"])
    agent_request = AgentRequest(
        request_id=request_id,
        conversation_id=conv_id,
        message=payload.message.strip(),
        conversation_history=payload.conversation_history,
        system_instructions=sys_instr,
        metadata=metadata,
        execution_config=config,
        runtime_config=container.runtime_config,
    )
    return agent_request, config, request_id


@router.post("/chat", response_model=ChatResponsePayload)
def chat_endpoint(payload: ChatRequestPayload, request: Request, container: AppContainer = Depends(get_container)) -> ChatResponsePayload:
    agent_request, config, request_id = _prepare_chat_request(payload, request, container)
    response: AgentResponse = container.agent_orchestrator.execute(agent_request)
    critique = response.diagnostics.get("critique") if isinstance(response.diagnostics, dict) else None
    verification = response.diagnostics.get("verification") if isinstance(response.diagnostics, dict) else None
    telemetry = _build_telemetry(response, config.get("context_window_tokens"))
    return ChatResponsePayload(answer=response.answer, execution_id=response.execution_id, conversation_id=response.conversation_id, status=response.status.value, iterations=response.iterations, retrieval_used=response.used_retrieval, memory_used=response.used_memory, tools_used=response.used_tools, critique_status="passed" if critique and critique.get("passed") else "failed" if critique else None, verification_status=verification.get("status") if verification else None, provenance=response.provenance, telemetry=telemetry, request_id=request_id)


@router.post("/executions", response_model=dict[str, Any], status_code=status.HTTP_201_CREATED)
def create_execution_endpoint(payload: ExecutionRequestPayload, container: AppContainer = Depends(get_container)) -> dict[str, Any]:
    conversation_id = payload.conversation_id or f"conv-{uuid.uuid4().hex[:12]}"
    response = container.agent_orchestrator.execute(AgentRequest(request_id=f"req-{uuid.uuid4().hex[:12]}", conversation_id=conversation_id, message=payload.task_description, metadata=payload.metadata, execution_config=payload.execution_config, runtime_config=container.runtime_config))
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
