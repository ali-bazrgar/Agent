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


def _check_database(container: AppContainer) -> dict[str, Any]:
    try:
        with container.database_engine.connect() as connection:
            connection.execute("SELECT 1").fetchone()
        return {"status": "healthy", "message": "database connection is available"}
    except Exception as exc:
        return {"status": "unavailable", "message": f"database check failed: {exc}"}


def _tool_diagnostics(container: AppContainer) -> dict[str, Any]:
    definitions = container.tool_registry.list_tools()
    return {
        "status": "healthy" if definitions else "degraded",
        "enabled_tools": [definition.name for definition in definitions],
        "count": len(definitions),
    }


def _web_diagnostics(container: AppContainer) -> dict[str, Any]:
    provider = container.web_provider
    if provider is None:
        return {"status": "unconfigured", "message": "no external web search provider configured"}
    return {
        "status": "configured",
        "provider": provider.__class__.__name__,
    }


@router.get("/health")
def health(container: AppContainer = Depends(get_container)) -> dict[str, object]:
    settings = get_settings()

    llm_health = _check_provider_health(container.llm_provider, "llm")
    embedding_health = _check_provider_health(container.embedding_provider, "embedding")
    reranker_health = _check_provider_health(container.reranker_provider, "reranker")
    database_health = _check_database(container)
    tools_health = _tool_diagnostics(container)
    web_health = _web_diagnostics(container)

    providers = {
        "llm": llm_health,
        "embedding": embedding_health,
        "reranker": reranker_health,
    }

    all_providers_healthy = all(p["status"] == ProviderHealthStatus.HEALTHY.value for p in providers.values())
    dependencies_healthy = database_health["status"] == "healthy" and tools_health["status"] == "healthy"
    overall_status = "ok" if all_providers_healthy and dependencies_healthy else "degraded"

    return {
        "status": overall_status,
        "environment": settings.environment,
        "debug": settings.debug,
        "database": {"path": str(settings.database_path_resolved), **database_health},
        "storage": str(settings.storage_path_resolved),
        "providers": providers,
        "tools": tools_health,
        "web_search": web_health,
    }
