from fastapi.testclient import TestClient

from superagent.api.app import create_app
from superagent.api.chat import get_container
from superagent.application.container import AppContainer
from superagent.database.config import DatabaseConfig
from superagent.database.engine import DatabaseEngine
from superagent.providers.contracts import LLMProvider, LLMRequest, LLMResponse, ProviderHealth, ProviderHealthStatus, ProviderCapabilities


class MockChatLLM(LLMProvider):
    def complete(self, request: LLMRequest) -> LLMResponse:
        return LLMResponse(text="Hello from SuperAgent API!", model_id="mock-llm")

    def check_health(self) -> ProviderHealth:
        return ProviderHealth(name="mock", status=ProviderHealthStatus.HEALTHY)

    def capabilities(self) -> ProviderCapabilities:
        return ProviderCapabilities(chat=True)


def test_chat_api_endpoint(tmp_path):
    # Setup test container with mock LLM and SQLite DB
    db_file = tmp_path / "test_api.db"
    db_engine = DatabaseEngine(DatabaseConfig(path=db_file))
    db_engine.ensure_ready()

    container = AppContainer(
        database_engine=db_engine,
        llm_provider=MockChatLLM(),
    )

    # Override container in chat endpoint
    app = create_app()
    app.dependency_overrides[get_container] = lambda: container

    client = TestClient(app)

    response = client.post(
        "/api/v1/chat",
        json={
            "message": "Hello, SuperAgent!",
            "conversation_id": "conv-test-1",
        },
    )

    assert response.status_code == 200
    data = response.json()
    assert data["answer"] == "Hello from SuperAgent API!"
    assert data["status"] == "completed"
    assert "execution_id" in data

    # Test GET execution status endpoint
    exec_id = data["execution_id"]
    exec_res = client.get(f"/api/v1/executions/{exec_id}")
    assert exec_res.status_code == 200
    exec_data = exec_res.json()
    assert exec_data["execution_id"] == exec_id
    assert exec_data["status"] == "completed"
