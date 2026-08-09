from __future__ import annotations

import time
import uuid
from collections.abc import Awaitable, Callable

from fastapi import FastAPI, Request, Response

from superagent.api.chat import router as chat_router
from superagent.api.configuration import router as configuration_router
from superagent.api.diagnostics import router as diagnostics_router
from superagent.api.documents import router as documents_router
from superagent.api.engine_manager import router as engine_manager_router
from superagent.api.health import router as health_router
from superagent.api.knowledge_graph import router as knowledge_graph_router
from superagent.api.learning import router as learning_router
from superagent.api.llama_profiles import router as llama_profiles_router
from superagent.api.memories import router as memories_router
from superagent.api.system_picker import router as system_picker_router
from superagent.api.tools import router as tools_router
from superagent.observability.diagnostics import get_diagnostic_store

_API_ROUTERS = (
    health_router,
    chat_router,
    tools_router,
    learning_router,
    memories_router,
    documents_router,
    knowledge_graph_router,
    configuration_router,
    llama_profiles_router,
    engine_manager_router,
    system_picker_router,
    diagnostics_router,
)


def _register_api_routers(app: FastAPI, prefix: str) -> None:
    for router in _API_ROUTERS:
        app.include_router(router, prefix=prefix)


def create_app() -> FastAPI:
    """Create and configure the FastAPI application with request tracing."""
    app = FastAPI(title="Super Agent API", version="0.3.1", docs_url="/docs", redoc_url="/redoc")
    diagnostics = get_diagnostic_store()
    app.state.diagnostics = diagnostics

    @app.middleware("http")
    async def trace_requests(request: Request, call_next: Callable[[Request], Awaitable[Response]]) -> Response:
        request_id = request.headers.get("x-request-id") or uuid.uuid4().hex
        started = time.perf_counter()
        response: Response | None = None
        error: str | None = None
        try:
            response = await call_next(request)
            return response
        except Exception as exc:
            error = f"{type(exc).__name__}: {exc}"
            raise
        finally:
            diagnostics.record(
                "api.request",
                request_id=request_id,
                method=request.method,
                path=request.url.path,
                query=str(request.url.query)[:2000],
                status_code=response.status_code if response else 500,
                duration_ms=round((time.perf_counter() - started) * 1000, 3),
                error=error,
            )
            if response is not None:
                response.headers["x-request-id"] = request_id

    _register_api_routers(app, "/v1")
    _register_api_routers(app, "/api/v1")
    return app


app = create_app()
