from __future__ import annotations

import json
from pathlib import Path

from fastapi.testclient import TestClient

from superagent.api.app import create_app
from superagent.observability.diagnostics import DiagnosticStore


def test_diagnostic_store_scrubs_secrets(tmp_path: Path) -> None:
    store = DiagnosticStore(tmp_path)
    event = store.record("test.event", authorization="Bearer super-secret", api_key="abc123", nested={"token": "xyz"}, ok="value")
    assert event["ok"] == "value"
    raw = store.path.read_text(encoding="utf-8")
    assert "super-secret" not in raw
    assert "abc123" not in raw
    assert "xyz" not in raw
    assert "[REDACTED]" in raw


def test_diagnostics_api_accepts_and_exports(tmp_path: Path, monkeypatch) -> None:
    import superagent.api.diagnostics as diagnostics_api

    store = DiagnosticStore(tmp_path)
    monkeypatch.setattr(diagnostics_api, "store", store)
    client = TestClient(create_app())
    response = client.post("/api/v1/diagnostics/events", json={"type": "ui.click", "fields": {"target": "button"}})
    assert response.status_code == 202
    assert response.json()["session_id"] == store.session_id
    lines = store.path.read_text(encoding="utf-8").splitlines()
    assert any(json.loads(line)["type"] == "frontend.ui.click" for line in lines)
    export = client.get("/api/v1/diagnostics/export")
    assert export.status_code == 200
    assert export.headers["content-type"] == "application/zip"
