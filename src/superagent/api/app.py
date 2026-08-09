from __future__ import annotations

import os
import time
import uuid
from collections.abc import Awaitable, Callable

from fastapi import FastAPI, Request, Response
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

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


def _cors_origins() -> list[str]:
    raw = os.getenv("SUPERAGENT_CORS_ORIGINS", "http://127.0.0.1:3000,http://localhost:3000")
    return [origin.strip().rstrip("/") for origin in raw.split(",") if origin.strip()]


def _validation_message(exc: RequestValidationError) -> str:
    parts: list[str] = []
    for item in exc.errors():
        location = ".".join(str(value) for value in item.get("loc", [])) or "request"
        message = str(item.get("msg", "invalid value"))
        parts.append(f"{location}: {message}")
    return "Validation error: " + "; ".join(parts)


def create_app() -> FastAPI:
    """Create and configure the FastAPI application with request tracing."""
    app = FastAPI(title="Super Agent API", version="0.3.2", docs_url="/docs", redoc_url="/redoc")
    diagnostics = get_diagnostic_store()
    app.state.diagnostics = diagnostics

    app.add_middleware(
        CORSMiddleware,
        allow_origins=_cors_origins(),
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
        allow_headers=["*"],
        expose_headers=["x-request-id"],
    )

    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
        return JSONResponse(status_code=422, content={"detail": _validation_message(exc)})

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

    from fastapi.routing import APIRoute

    health_route = next((route for route in app.routes if getattr(route, "path", None) == "/v1/health"), None)
    if isinstance(health_route, APIRoute):
        app.add_api_route(
            "/health",
            health_route.endpoint,
            methods=["GET"],
            response_model=health_route.response_model,
            tags=["health"],
        )

    return app


app = create_app()
