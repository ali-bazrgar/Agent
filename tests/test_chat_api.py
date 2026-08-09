from fastapi.testclient import TestClient

from superagent.api.app import create_app
from superagent.api.chat import get_container
from superagent.application.container import AppContainer
from superagent.database.config import DatabaseConfig
from superagent.database.engine import DatabaseEngine
from superagent.providers.contracts import (
    LLMProvider,
    LLMRequest,
    LLMResponse,
    ProviderCapabilities,
    ProviderHealth,
    ProviderHealthStatus,
)


class MockChatLLM(LLMProvider):
    def complete(self, request: LLMRequest) -> LLMResponse:
        return LLMResponse(
            text="Hello from SuperAgent API!",
            model_id="mock-llm",
            token_usage=17,
            metadata={"timings": {"prompt_n": 12, "prompt_ms": 4.0, "predicted_n": 5, "predicted_ms": 10.0, "predicted_per_second": 500.0}},
        )

    def check_health(self) -> ProviderHealth:
        return ProviderHealth(name="mock", status=ProviderHealthStatus.HEALTHY)

    def capabilities(self) -> ProviderCapabilities:
        return ProviderCapabilities(chat=True)


def test_chat_api_endpoint(tmp_path):
    db_file = tmp_path / "test_api.db"
    db_engine = DatabaseEngine(DatabaseConfig(path=db_file))
    db_engine.ensure_ready()

    container = AppContainer(
        database_engine=db_engine,
        llm_provider=MockChatLLM(),
    )

    app = create_app()
    app.dependency_overrides[get_container] = lambda: container
    client = TestClient(app)

    response = client.post(
        "/v1/chat",
        headers={"x-request-id": "req-test-telemetry"},
        json={
            "message": "Hello, SuperAgent!",
            "conversation_id": "conv-test-1",
            "runtime_options": {"context_window": 4096},
        },
    )

    assert response.status_code == 200
    data = response.json()
    assert data["answer"] == "Hello from SuperAgent API!"
    assert data["status"] == "completed"
    assert "execution_id" in data
    assert data["request_id"] == "req-test-telemetry"
    assert data["telemetry"]["context_window"] == 4096
    assert data["telemetry"]["prompt_tokens"] == 12
    assert data["telemetry"]["output_tokens"] == 5
    assert data["telemetry"]["total_tokens"] == 17
    assert data["telemetry"]["generation_tps"] == 500.0
    assert data["telemetry"]["generation_ms"] == 10.0

    exec_id = data["execution_id"]
    exec_res = client.get(f"/v1/executions/{exec_id}")
    assert exec_res.status_code == 200
    exec_data = exec_res.json()
    assert exec_data["execution_id"] == exec_id
    assert exec_data["status"] == "completed"
