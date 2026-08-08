from __future__ import annotations

from collections.abc import Generator
from typing import Any

from fastapi import APIRouter, Depends

from superagent.application.container import AppContainer
from superagent.config.settings import get_settings
from superagent.providers.contracts import ProviderHealthStatus

router = APIRouter()


def get_container() -> Generator[AppContainer, None, None]:
    """Create a request-scoped container and close provider clients afterwards."""
    container = AppContainer()
    try:
        yield container
    finally:
        for provider in (
            container.llm_provider,
            container.embedding_provider,
            container.reranker_provider,
        ):
            close = getattr(provider, "close", None)
            if callable(close):
                close()


def _check_provider_health(provider: Any, name: str) -> dict[str, Any]:
    if provider is None:
        return {"name": name, "status": ProviderHealthStatus.UNAVAILABLE.value, "message": "provider not configured"}
    try:
        health_info = provider.check_health()
        status_val = health_info.status.value if hasattr(health_info.status, "value") else str(health_info.status)
        return {
            "name": getattr(health_info, "name", name),
            "status": status_val,
            "message": health_info.message,
            "details": getattr(health_info, "details", {}),
        }
    except Exception as exc:
        return {
            "name": name,
            "status": ProviderHealthStatus.UNAVAILABLE.value,
            "message": f"health check failed: {exc}",
            "details": {},
        }


@router.get("/health")
def health(container: AppContainer = Depends(get_container)) -> dict[str, object]:
    settings = get_settings()

    llm_health = _check_provider_health(container.llm_provider, "llm")
    embedding_health = _check_provider_health(container.embedding_provider, "embedding")
    reranker_health = _check_provider_health(container.reranker_provider, "reranker")

    providers = {
        "llm": llm_health,
        "embedding": embedding_health,
        "reranker": reranker_health,
    }

    all_healthy = all(p["status"] == ProviderHealthStatus.HEALTHY.value for p in providers.values())
    overall_status = "ok" if all_healthy else "degraded"

    return {
        "status": overall_status,
        "environment": settings.environment,
        "debug": settings.debug,
        "database": str(settings.database_path_resolved),
        "storage": str(settings.storage_path_resolved),
        "providers": providers,
    }
