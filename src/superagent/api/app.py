from __future__ import annotations

from fastapi import FastAPI

from superagent.api.chat import router as chat_router
from superagent.api.health import router as health_router
from superagent.api.tools import router as tools_router
from superagent.api.learning import router as learning_router
from superagent.api.memories import router as memories_router
from superagent.api.documents import router as documents_router
from superagent.api.memories import router as memories_router


def create_app() -> FastAPI:
    """Create the FastAPI application for SuperAgent."""

    app = FastAPI(title="Super Agent", version="0.1.0")
    
    @app.middleware("http")
    async def log_requests(request, call_next):
        response = await call_next(request)
        if response.status_code == 404:
            print(f"DEBUG: 404 for {request.url.path}")
        return response

    app.include_router(health_router, prefix="/v1")
    app.include_router(chat_router, prefix="/v1")
    app.include_router(tools_router, prefix="/v1")
    app.include_router(learning_router, prefix="/v1")
    app.include_router(memories_router, prefix="/v1")
    return app


app = create_app()
