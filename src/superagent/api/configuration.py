from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from superagent.api.chat import get_container
from superagent.application.container import AppContainer
from superagent.llm.runtime import ContextAllocationPolicy, ModelRuntimeConfig

router = APIRouter(prefix="/config", tags=["configuration"])


def _provider(base_url: str, model_id: str | None, provider: str) -> dict[str, object]:
    return {"provider": provider, "baseUrl": base_url, "modelId": model_id or "auto", "configured": bool(base_url)}


def _capabilities(provider: Any) -> dict[str, Any]:
    if provider is None:
        return {}
    try:
        return provider.capabilities().model_dump(mode="json")
    except Exception:
        return {}


class RuntimeUpdate(BaseModel):
    model_id: str | None = None
    context_window_tokens: int = Field(ge=256)
    max_output_tokens: int | None = Field(default=None, ge=1)
    temperature: float = Field(default=0.7, ge=0.0, le=2.0)
    top_p: float = Field(default=1.0, gt=0.0, le=1.0)
    timeout_seconds: float = Field(default=60.0, gt=0.0)
    context_allocation: ContextAllocationPolicy = Field(default_factory=ContextAllocationPolicy)


@router.get("")
def get_configuration(container: AppContainer = Depends(get_container)) -> dict[str, object]:
    settings = container.settings
    assert settings is not None
    runtime = container.runtime_config
    llm_capabilities = _capabilities(container.llm_provider)
    embedding_capabilities = _capabilities(container.embedding_provider)
    reranker_capabilities = _capabilities(container.reranker_provider)
    return {
        "environment": settings.environment,
        "debug": settings.debug,
        "llm": {**_provider(settings.llm_base_url, settings.llm_model_id, settings.llm_provider), "chatCompletionsPath": settings.llm_chat_completions_path, "healthPath": settings.llm_health_path, "maxOutputTokens": settings.llm_max_output_tokens, "temperature": settings.llm_temperature, "topP": settings.llm_top_p, "frequencyPenalty": settings.llm_frequency_penalty, "presencePenalty": settings.llm_presence_penalty, "seed": settings.llm_seed, "contextWindowTokens": settings.context_window_tokens, "apiKeyConfigured": bool(settings.provider_api_key), "runtime": runtime.model_dump(mode="json") if runtime else None, "capabilities": llm_capabilities},
        "embeddings": {**_provider(settings.embedding_base_url, settings.embedding_model_id, "llama.cpp"), "path": settings.embedding_path, "healthPath": settings.embedding_health_path, "dimensions": settings.embedding_dimensions, "capabilities": embedding_capabilities},
        "reranker": {**_provider(settings.reranker_base_url, settings.reranker_model_id, "llama.cpp"), "path": settings.reranker_path, "healthPath": settings.reranker_health_path, "topN": settings.reranker_top_n, "capabilities": reranker_capabilities},
        "agent": {"maxModelCalls": settings.max_model_calls, "maxToolCalls": settings.max_tool_calls, "maxRetries": settings.max_retries, "maxExecutionTimeSeconds": settings.max_execution_time_seconds, "maxTotalModelTokens": settings.max_total_model_tokens, "llmDrivenTools": settings.llm_driven_tools, "llmDrivenMemory": settings.llm_driven_memory, "automaticMemoryExtractionEnabled": settings.automatic_memory_extraction_enabled},
        "context": {"contextWindowTokens": settings.context_window_tokens, "modelMaximumTokens": llm_capabilities.get("context_window_tokens")},
        "learning": {"enabled": settings.learning_enabled, "dailyReviewLimit": settings.daily_review_limit, "newCardsPerDay": settings.new_cards_per_day},
        "database": {"path": str(settings.database_path_resolved), "storagePath": str(settings.storage_path_resolved)},
        "observability": {"logLevel": settings.log_level},
        "runtime": {"configurationSource": "environment/.env + runtime profile", "mutableAtRuntime": True},
    }


@router.get("/models")
def get_model_runtime_catalog(container: AppContainer = Depends(get_container)) -> dict[str, Any]:
    settings = container.settings
    assert settings is not None
    llm_capabilities = _capabilities(container.llm_provider)
    context_maximum = llm_capabilities.get("context_window_tokens")
    return {
        "llm": {"provider": settings.llm_provider, "modelId": settings.llm_model_id, "baseUrl": settings.llm_base_url, "runtime": container.runtime_config.model_dump(mode="json") if container.runtime_config else None, "capabilities": llm_capabilities, "controls": {"temperature": {"min": 0.0, "max": 2.0, "step": 0.01, "value": settings.llm_temperature}, "topP": {"min": 0.01, "max": 1.0, "step": 0.01, "value": settings.llm_top_p}, "frequencyPenalty": {"min": -2.0, "max": 2.0, "step": 0.01, "value": settings.llm_frequency_penalty}, "presencePenalty": {"min": -2.0, "max": 2.0, "step": 0.01, "value": settings.llm_presence_penalty}, "maxOutputTokens": {"min": 1, "max": llm_capabilities.get("max_output_tokens"), "value": settings.llm_max_output_tokens}, "contextWindowTokens": {"min": 256, "max": context_maximum, "value": container.runtime_config.context_window_tokens if container.runtime_config else settings.context_window_tokens, "modelMaximum": context_maximum, "readOnly": False}, "seed": {"value": settings.llm_seed, "nullable": True}, "maxTotalModelTokens": {"min": 0, "value": settings.max_total_model_tokens, "unlimitedWhen": 0}}},
        "embedding": {"provider": "llama.cpp", "modelId": settings.embedding_model_id, "baseUrl": settings.embedding_base_url, "path": settings.embedding_path, "capabilities": _capabilities(container.embedding_provider), "controls": {"modelId": {"value": settings.embedding_model_id, "nullable": True}, "dimensions": {"value": settings.embedding_dimensions, "nullable": True}}},
        "reranker": {"provider": "llama.cpp", "modelId": settings.reranker_model_id, "baseUrl": settings.reranker_base_url, "path": settings.reranker_path, "capabilities": _capabilities(container.reranker_provider), "controls": {"modelId": {"value": settings.reranker_model_id, "nullable": True}, "topN": {"min": 1, "value": settings.reranker_top_n, "nullable": True}}},
    }


@router.put("/runtime")
def update_runtime(payload: RuntimeUpdate, container: AppContainer = Depends(get_container)) -> dict[str, Any]:
    """Apply the active model runtime profile without restarting the API process."""
    capabilities = _capabilities(container.llm_provider)
    maximum = capabilities.get("context_window_tokens")
    if isinstance(maximum, int) and payload.context_window_tokens > maximum:
        raise HTTPException(status_code=422, detail=f"context_window_tokens exceeds the selected model capability ({maximum}).")
    runtime = ModelRuntimeConfig(**payload.model_dump())
    container.runtime_config = runtime
    container.effective_capabilities = capabilities | {"context_window_tokens": runtime.context_window_tokens, "max_output_tokens": runtime.max_output_tokens}
    configure_runtime = getattr(container.llm_provider, "configure_runtime", None)
    if callable(configure_runtime):
        configure_runtime(runtime)
    if container._agent_orchestrator is not None:
        container._agent_orchestrator.runtime_config = runtime
    return {"ok": True, "runtime": runtime.model_dump(mode="json")}
