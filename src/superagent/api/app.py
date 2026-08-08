from __future__ import annotations

import logging
from collections.abc import Awaitable, Callable

from fastapi import FastAPI, Request, Response

from superagent.api.chat import router as chat_router
from superagent.api.documents import router as documents_router
from superagent.api.health import router as health_router
from superagent.api.learning import router as learning_router
from superagent.api.memories import router as memories_router
from superagent.api.tools import router as tools_router

logger = logging.getLogger(__name__)


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    app = FastAPI(
        title="Super Agent API",
        version="0.1.0",
        docs_url="/docs",
        redoc_url="/redoc",
    )

    @app.middleware("http")
    async def log_requests(
        request: Request,
        call_next: Callable[[Request], Awaitable[Response]],
    ) -> Response:
        response = await call_next(request)
        if response.status_code >= 400:
            logger.warning("HTTP %s %s -> %s", request.method, request.url.path, response.status_code)
        return response

    app.include_router(health_router, prefix="/v1")
    app.include_router(chat_router, prefix="/v1")
    app.include_router(tools_router, prefix="/v1")
    app.include_router(learning_router, prefix="/v1")
    app.include_router(memories_router, prefix="/v1")
    app.include_router(documents_router, prefix="/v1")
    return app


app = create_app()
