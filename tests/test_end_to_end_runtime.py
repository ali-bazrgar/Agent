from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from superagent.agents.models import AgentRequest, AgentRoute, AgentExecutionStatus
from superagent.agents.orchestrator import AgentOrchestrator
from superagent.api.app import create_app
from superagent.api.chat import get_container
from superagent.application.container import AppContainer
from superagent.database.config import DatabaseConfig
from superagent.database.engine import DatabaseEngine
from superagent.providers.contracts import (
    LLMProvider,
    LLMRequest,
    LLMResponse,
    ProviderHealth,
    ProviderHealthStatus,
    ProviderCapabilities,
    WebResearchProvider,
    WebResearchRequest,
    WebResearchResponse,
)


class MockE2ELLM(LLMProvider):
    def complete(self, request: LLMRequest) -> LLMResponse:
        prompt_lower = request.prompt.lower()
        if "calculate" in prompt_lower or "123 * 45" in prompt_lower:
            return LLMResponse(text="The result is 5535.", model_id="mock-e2e")
        elif "python" in prompt_lower:
            return LLMResponse(text="Python is a high-level programming language.", model_id="mock-e2e")
        elif "research" in prompt_lower:
            return LLMResponse(text="According to recent web research, quantum computing has advanced.", model_id="mock-e2e")
        return LLMResponse(text=f"Processed query: {request.prompt}", model_id="mock-e2e")

    def check_health(self) -> ProviderHealth:
        return ProviderHealth(name="mock-llm", status=ProviderHealthStatus.HEALTHY)

    def capabilities(self) -> ProviderCapabilities:
        return ProviderCapabilities(chat=True, streaming=True)


class FailingLLM(LLMProvider):
    def complete(self, request: LLMRequest) -> LLMResponse:
        raise RuntimeError("LLM provider down")

    def check_health(self) -> ProviderHealth:
        return ProviderHealth(name="failing-llm", status=ProviderHealthStatus.UNAVAILABLE)

    def capabilities(self) -> ProviderCapabilities:
        return ProviderCapabilities(chat=True)





def test_e2e_direct_execution(tmp_path):
    db_file = tmp_path / "e2e_direct.db"
    db_engine = DatabaseEngine(DatabaseConfig(path=db_file))
    db_engine.ensure_ready()

    container = AppContainer(
        database_engine=db_engine,
        llm_provider=MockE2ELLM(),
    )

    orchestrator = container.agent_orchestrator
    req = AgentRequest(
        request_id="req-dir",
        conversation_id="conv-dir",
        message="What is Python?",
    )
    res = orchestrator.execute(req)
    assert res.status == AgentExecutionStatus.COMPLETED
    assert "Python is a high-level" in res.answer
    assert res.execution_id is not None


def test_e2e_chat_api_streaming_and_execution(tmp_path):
    db_file = tmp_path / "e2e_api.db"
    db_engine = DatabaseEngine(DatabaseConfig(path=db_file))
    db_engine.ensure_ready()

    container = AppContainer(
        database_engine=db_engine,
        llm_provider=MockE2ELLM(),
    )

    app = create_app()
    app.dependency_overrides[get_container] = lambda: container
    client = TestClient(app)

    # Test Chat POST
    response = client.post(
        "/api/v1/chat",
        json={"message": "What is Python?", "conversation_id": "conv-api-1"},
    )
    assert response.status_code == 200
    data = response.json()
    assert "Python" in data["answer"]
    exec_id = data["execution_id"]

    # Test Execution GET
    exec_res = client.get(f"/api/v1/executions/{exec_id}")
    assert exec_res.status_code == 200
    exec_data = exec_res.json()
    assert exec_data["status"] == "completed"


def test_e2e_failure_recovery(tmp_path):
    db_file = tmp_path / "e2e_fail.db"
    db_engine = DatabaseEngine(DatabaseConfig(path=db_file))
    db_engine.ensure_ready()

    container = AppContainer(
        database_engine=db_engine,
        llm_provider=FailingLLM(),
    )

    orchestrator = container.agent_orchestrator
    req = AgentRequest(
        request_id="req-fail",
        conversation_id="conv-fail",
        message="Hello",
    )
    res = orchestrator.execute(req)
    assert res.status == AgentExecutionStatus.FAILED
    assert "Execution failed during generation" in res.answer or "error" in res.answer.lower()
