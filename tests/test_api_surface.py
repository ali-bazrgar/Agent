from __future__ import annotations

from fastapi.testclient import TestClient

from superagent.api.app import create_app
from superagent.database.config import DatabaseConfig
from superagent.database.engine import DatabaseEngine
from superagent.application.container import AppContainer


def test_knowledge_graph_endpoint_is_available(tmp_path, monkeypatch) -> None:
    engine = DatabaseEngine(DatabaseConfig(path=tmp_path / "graph.sqlite3", timeout_seconds=5.0))
    engine.ensure_ready()
    container = AppContainer(database_engine=engine)
    from superagent.api import knowledge_graph as graph_module
    monkeypatch.setattr(graph_module, "get_container", lambda: container)
    response = TestClient(create_app()).get("/api/v1/knowledge-graph")
    assert response.status_code == 200
    payload = response.json()
    assert payload["nodes"] == []
    assert payload["edges"] == []
    assert payload["stats"]["nodes"] == 0


def test_runtime_configuration_endpoint_is_available(tmp_path, monkeypatch) -> None:
    engine = DatabaseEngine(DatabaseConfig(path=tmp_path / "config.sqlite3", timeout_seconds=5.0))
    engine.ensure_ready()
    container = AppContainer(database_engine=engine)
    from superagent.api import configuration as config_module
    monkeypatch.setattr(config_module, "get_container", lambda: container)
    response = TestClient(create_app()).get("/api/v1/config")
    assert response.status_code == 200
    payload = response.json()
    assert payload["llm"]["provider"] == "llama.cpp"
    assert payload["runtime"]["mutableAtRuntime"] is False
