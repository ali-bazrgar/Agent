from __future__ import annotations

import time
from collections.abc import Generator
from concurrent.futures import ThreadPoolExecutor
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
        return {"name": name, "status": ProviderHealthStatus.UNAVAILABLE.value, "message": "provider not configured", "details": {}}
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
    provider_specs = ((container.llm_provider, "llm"), (container.embedding_provider, "embedding"), (container.reranker_provider, "reranker"))
    with ThreadPoolExecutor(max_workers=3, thread_name_prefix="health") as executor:
        futures = [executor.submit(_check_provider_health, provider, name) for provider, name in provider_specs]
        provider_results = [future.result() for future in futures]
    providers = {item["name"] if item.get("name") in {"llm", "embedding", "reranker"} else name: item for item, (_, name) in zip(provider_results, provider_specs)}
    db_status, db_error = _check_database(container)
    storage_status = "healthy" if settings.storage_path_resolved.exists() else "missing"
    providers_healthy = all(item["status"] == ProviderHealthStatus.HEALTHY.value for item in providers.values())
    dependency_status = "healthy" if providers_healthy and db_status == "healthy" and storage_status == "healthy" else "degraded"
    return {
        "status": "ok" if providers_healthy else "degraded",
        "dependency_status": dependency_status,
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
