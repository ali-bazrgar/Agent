from __future__ import annotations

from fastapi.testclient import TestClient

from superagent.api.app import create_app


def test_health_endpoint_returns_status(temporary_settings) -> None:
    app = create_app()
    client = TestClient(app)

    response = client.get("/api/v1/health")
    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] in {"ok", "degraded"}
    assert payload["environment"] == "development"
