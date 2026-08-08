from __future__ import annotations

import logging
from collections.abc import Awaitable, Callable

from fastapi import FastAPI, Request, Response

from superagent.api.chat import router as chat_router
from superagent.api.configuration import router as configuration_router
from superagent.api.documents import router as documents_router
from superagent.api.health import router as health_router
from superagent.api.knowledge_graph import router as knowledge_graph_router
from superagent.api.learning import router as learning_router
from superagent.api.memories import router as memories_router
from superagent.api.tools import router as tools_router

logger = logging.getLogger(__name__)

_API_ROUTERS = (
    health_router,
    chat_router,
    tools_router,
    learning_router,
    memories_router,
    documents_router,
    knowledge_graph_router,
    configuration_router,
)


def _register_api_routers(app: FastAPI, prefix: str) -> None:
    for router in _API_ROUTERS:
        app.include_router(router, prefix=prefix)


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    app = FastAPI(title="Super Agent API", version="0.2.0", docs_url="/docs", redoc_url="/redoc")

    @app.middleware("http")
    async def log_requests(request: Request, call_next: Callable[[Request], Awaitable[Response]]) -> Response:
        response = await call_next(request)
        if response.status_code >= 400:
            logger.warning("HTTP %s %s -> %s", request.method, request.url.path, response.status_code)
        return response

    _register_api_routers(app, "/v1")
    _register_api_routers(app, "/api/v1")
    return app


app = create_app()
