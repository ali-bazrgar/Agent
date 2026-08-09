from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends

from superagent.api.chat import get_container
from superagent.application.container import AppContainer

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
        "runtime": {"configurationSource": "environment/.env", "mutableAtRuntime": False},
    }


router.get("")(get_configuration)


@router.get("/models")
def get_model_runtime_catalog(container: AppContainer = Depends(get_container)) -> dict[str, Any]:
    """Return the frontend-safe model/runtime surface without exposing secrets."""
    settings = container.settings
    assert settings is not None
    llm_capabilities = _capabilities(container.llm_provider)
    context_maximum = llm_capabilities.get("context_window_tokens")
    return {
        "llm": {"provider": settings.llm_provider, "modelId": settings.llm_model_id, "baseUrl": settings.llm_base_url, "runtime": container.runtime_config.model_dump(mode="json") if container.runtime_config else None, "capabilities": llm_capabilities, "controls": {"temperature": {"min": 0.0, "max": 2.0, "step": 0.01, "value": settings.llm_temperature}, "topP": {"min": 0.01, "max": 1.0, "step": 0.01, "value": settings.llm_top_p}, "frequencyPenalty": {"min": -2.0, "max": 2.0, "step": 0.01, "value": settings.llm_frequency_penalty}, "presencePenalty": {"min": -2.0, "max": 2.0, "step": 0.01, "value": settings.llm_presence_penalty}, "maxOutputTokens": {"min": 1, "max": llm_capabilities.get("max_output_tokens"), "value": settings.llm_max_output_tokens}, "contextWindowTokens": {"min": 256, "max": context_maximum, "value": settings.context_window_tokens, "modelMaximum": context_maximum, "readOnly": False}, "seed": {"value": settings.llm_seed, "nullable": True}, "maxTotalModelTokens": {"min": 0, "value": settings.max_total_model_tokens, "unlimitedWhen": 0}}},
        "embedding": {"provider": "llama.cpp", "modelId": settings.embedding_model_id, "baseUrl": settings.embedding_base_url, "path": settings.embedding_path, "capabilities": llm_capabilities if settings.embedding_base_url == settings.llm_base_url else _capabilities(container.embedding_provider), "controls": {"modelId": {"value": settings.embedding_model_id, "nullable": True}, "dimensions": {"value": settings.embedding_dimensions, "nullable": True}}},
        "reranker": {"provider": "llama.cpp", "modelId": settings.reranker_model_id, "baseUrl": settings.reranker_base_url, "path": settings.reranker_path, "capabilities": _capabilities(container.reranker_provider), "controls": {"modelId": {"value": settings.reranker_model_id, "nullable": True}, "topN": {"min": 1, "value": settings.reranker_top_n, "nullable": True}}},
    }
