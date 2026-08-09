from __future__ import annotations

from fastapi import APIRouter, Depends

from superagent.api.chat import get_container
from superagent.application.container import AppContainer

router = APIRouter(prefix="/config", tags=["configuration"])


def _provider(base_url: str, model_id: str | None, provider: str) -> dict[str, object]:
    return {"provider": provider, "baseUrl": base_url, "modelId": model_id or "auto", "configured": bool(base_url)}


@router.get("")
def get_configuration(container: AppContainer = Depends(get_container)) -> dict[str, object]:
    settings = container.settings
    assert settings is not None
    return {
        "environment": settings.environment,
        "debug": settings.debug,
        "llm": {
            **_provider(settings.llm_base_url, settings.llm_model_id, settings.llm_provider),
            "chatCompletionsPath": settings.llm_chat_completions_path,
            "healthPath": settings.llm_health_path,
            "maxOutputTokens": settings.llm_max_output_tokens,
            "temperature": settings.llm_temperature,
            "contextWindowTokens": settings.context_window_tokens,
            "apiKeyConfigured": bool(settings.provider_api_key),
        },
        "embeddings": _provider(settings.embedding_base_url, settings.embedding_model_id, "llama.cpp"),
        "reranker": _provider(settings.reranker_base_url, settings.reranker_model_id, "llama.cpp"),
        "agent": {
            "maxModelCalls": settings.max_model_calls,
            "maxToolCalls": settings.max_tool_calls,
            "maxRetries": settings.max_retries,
            "maxExecutionTimeSeconds": settings.max_execution_time_seconds,
        },
        "context": {"contextWindowTokens": settings.context_window_tokens},
        "learning": {"enabled": settings.learning_enabled, "dailyReviewLimit": settings.daily_review_limit, "newCardsPerDay": settings.new_cards_per_day},
        "database": {"path": str(settings.database_path_resolved), "storagePath": str(settings.storage_path_resolved)},
        "observability": {"logLevel": settings.log_level},
        "runtime": {"configurationSource": "environment/.env", "mutableAtRuntime": False},
    }
