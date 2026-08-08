from __future__ import annotations

import time
from collections.abc import Generator
from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, Depends

from superagent.application.container import AppContainer
from superagent.config.settings import get_settings
from superagent.providers.contracts import ProviderHealthStatus

router = APIRouter()
_STARTED_AT = time.monotonic()


def get_container() -> Generator[AppContainer, None, None]:
    container = AppContainer()
    try:
        yield container
    finally:
        for provider in (container.llm_provider, container.embedding_provider, container.reranker_provider):
            close = getattr(provider, "close", None)
            if callable(close):
                close()


def _check_provider_health(provider: Any, name: str) -> dict[str, Any]:
    if provider is None:
        return {"name": name, "status": ProviderHealthStatus.UNAVAILABLE.value, "message": "provider not configured"}
    try:
        health_info = provider.check_health()
        status_val = health_info.status.value if hasattr(health_info.status, "value") else str(health_info.status)
        return {"name": getattr(health_info, "name", name), "status": status_val, "message": health_info.message, "details": getattr(health_info, "details", {})}
    except Exception as exc:
        return {"name": name, "status": ProviderHealthStatus.UNAVAILABLE.value, "message": f"health check failed: {exc}", "details": {}}


def _check_database(container: AppContainer) -> tuple[str, str | None]:
    try:
        with container.database_engine.connect() as connection:
            connection.execute("SELECT 1").fetchone()
        return "healthy", None
    except Exception as exc:
        return "unavailable", str(exc)


@router.get("/health")
def health(container: AppContainer = Depends(get_container)) -> dict[str, object]:
    settings = get_settings()
    llm_health = _check_provider_health(container.llm_provider, "llm")
    embedding_health = _check_provider_health(container.embedding_provider, "embedding")
    reranker_health = _check_provider_health(container.reranker_provider, "reranker")
    db_status, db_error = _check_database(container)
    storage_status = "healthy" if settings.storage_path_resolved.exists() else "missing"
    providers = {"llm": llm_health, "embedding": embedding_health, "reranker": reranker_health}
    all_healthy = db_status == "healthy" and storage_status == "healthy" and all(p["status"] == ProviderHealthStatus.HEALTHY.value for p in providers.values())
    return {
        "status": "ok" if all_healthy else "degraded",
        "environment": settings.environment,
        "debug": settings.debug,
        "database": str(settings.database_path_resolved),
        "database_status": db_status,
        "database_error": db_error,
        "storage": str(settings.storage_path_resolved),
        "storage_status": storage_status,
        "uptime_seconds": round(time.monotonic() - _STARTED_AT, 3),
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "providers": providers,
    }
