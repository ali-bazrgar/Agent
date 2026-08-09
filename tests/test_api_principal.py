from __future__ import annotations

from fastapi import FastAPI
from fastapi.testclient import TestClient

from superagent.api.auth import get_principal


def test_default_principal_is_explicitly_anonymous(monkeypatch) -> None:
    monkeypatch.delenv("SUPERAGENT_DEFAULT_PRINCIPAL_ID", raising=False)
    monkeypatch.setenv("SUPERAGENT_TRUST_PRINCIPAL_HEADER", "false")
    app = FastAPI()
    app.get("/principal")(lambda principal=__import__("fastapi").Depends(get_principal): principal)
    response = TestClient(app).get("/principal")
    assert response.status_code == 200
    assert response.json()["principal_id"] == "anonymous"
    assert response.json()["principal_type"] == "anonymous"


def test_local_default_principal_is_used_without_body_identity(monkeypatch) -> None:
    monkeypatch.setenv("SUPERAGENT_DEFAULT_PRINCIPAL_ID", "local-user")
    monkeypatch.setenv("SUPERAGENT_TRUST_PRINCIPAL_HEADER", "false")
    app = FastAPI()
    app.get("/principal")(lambda principal=__import__("fastapi").Depends(get_principal): principal)
    response = TestClient(app).get("/principal")
    assert response.status_code == 200
    assert response.json()["principal_id"] == "local-user"


def test_trusted_header_mode_requires_header(monkeypatch) -> None:
    monkeypatch.delenv("SUPERAGENT_DEFAULT_PRINCIPAL_ID", raising=False)
    monkeypatch.setenv("SUPERAGENT_TRUST_PRINCIPAL_HEADER", "true")
    app = FastAPI()
    app.get("/principal")(lambda principal=__import__("fastapi").Depends(get_principal): principal)
    client = TestClient(app)
    assert client.get("/principal").status_code == 401
    response = client.get("/principal", headers={"X-SuperAgent-Principal": "verified-user"})
    assert response.status_code == 200
    assert response.json()["principal_id"] == "verified-user"
