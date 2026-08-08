from __future__ import annotations

from fastapi import APIRouter, Request
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field

from superagent.observability.diagnostics import DiagnosticStore

router = APIRouter(prefix="/diagnostics", tags=["diagnostics"])
store = DiagnosticStore()


class DiagnosticEvent(BaseModel):
    type: str = Field(min_length=1, max_length=120)
    fields: dict[str, object] = Field(default_factory=dict)


@router.get("/status")
def diagnostic_status() -> dict[str, object]:
    return {"enabled": True, "session_id": store.session_id, "path": str(store.path)}


@router.post("/events", status_code=202)
def record_diagnostic_event(event: DiagnosticEvent, request: Request) -> dict[str, object]:
    recorded = store.record(
        event.type,
        source="frontend",
        client_host=request.client.host if request.client else None,
        **event.fields,
    )
    return {"accepted": True, "event_id": recorded["event_id"], "session_id": store.session_id}


@router.post("/export")
def export_diagnostics() -> FileResponse:
    path = store.export_zip()
    return FileResponse(path, media_type="application/zip", filename=path.name)
