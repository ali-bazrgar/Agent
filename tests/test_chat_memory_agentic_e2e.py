from fastapi.testclient import TestClient

from superagent.api.app import create_app
from superagent.api.chat import get_container
from superagent.application.container import AppContainer
from superagent.config.settings import Settings
from superagent.database.config import DatabaseConfig
from superagent.database.engine import DatabaseEngine
from superagent.llm.agentic_provider import AgenticLLMProvider
from superagent.models.domain import MemoryScope
from superagent.providers.contracts import (
    LLMProvider,
    LLMRequest,
    LLMResponse,
    LLMToolCall,
    ProviderCapabilities,
    ProviderHealth,
    ProviderHealthStatus,
)


class MemoryAgentFakeLLM(LLMProvider):
    """Deterministic model for exercising the real /chat agentic tool loop."""

    def __init__(self) -> None:
        self.calls: list[LLMRequest] = []

    def complete(self, request: LLMRequest) -> LLMResponse:
        self.calls.append(request)
        tool_messages = [m for m in request.messages if m.get("role") == "tool"]
        user_text = request.prompt

        if "پایتون" in user_text and not tool_messages:
            return LLMResponse(
                model_id="memory-agent-fake",
                tool_calls=[LLMToolCall(id="call-memory-write-1", name="memory.write", arguments={"content": "پایتون زبان خوبی هست. من پایتون را دوست دارم.", "kind": "user", "importance": 0.9})],
            )

        if "چه زبان برنامه" in user_text and not tool_messages:
            return LLMResponse(
                model_id="memory-agent-fake",
                tool_calls=[LLMToolCall(id="call-memory-search-1", name="memory.search", arguments={"query": "زبان برنامه نویسی مورد علاقه کاربر", "limit": 5})],
            )

        if tool_messages:
            content = tool_messages[-1].get("content", "")
            if "پایتون" in user_text and "memory.write" not in content:
                return LLMResponse(text="ذخیره شد.", model_id="memory-agent-fake")
            if "پایتون" in content:
                return LLMResponse(text="شما پایتون را دوست دارید.", model_id="memory-agent-fake")

        return LLMResponse(text="اطلاعاتی پیدا نشد.", model_id="memory-agent-fake")

    def check_health(self) -> ProviderHealth:
        return ProviderHealth(name="memory-agent-fake", status=ProviderHealthStatus.HEALTHY)

    def capabilities(self) -> ProviderCapabilities:
        return ProviderCapabilities(chat=True, tool_calling=True)


def _make_client(tmp_path, monkeypatch):
    monkeypatch.setenv("SUPERAGENT_TRUST_PRINCIPAL_HEADER", "true")
    monkeypatch.delenv("SUPERAGENT_DEFAULT_PRINCIPAL_ID", raising=False)
    db_file = tmp_path / "agentic-memory-e2e.db"
    database = DatabaseEngine(DatabaseConfig(path=db_file))
    database.ensure_ready()
    fake = MemoryAgentFakeLLM()
    settings = Settings(
        database_path=str(db_file),
        llm_provider="openai_compatible",
        llm_model_id="memory-agent-fake",
        llm_driven_tools=True,
        require_verified_capabilities=False,
        tools_enabled=True,
    )
    container = AppContainer(settings=settings, database_engine=database, llm_provider=fake)
    app = create_app()
    app.dependency_overrides[get_container] = lambda: container
    return TestClient(app), container, fake


def _chat(client: TestClient, principal: str, message: str, conversation_id: str):
    return client.post(
        "/v1/chat",
        headers={"X-SuperAgent-Principal": principal},
        json={"message": message, "conversation_id": conversation_id, "execution_config": {"llm_driven_tools": True}},
    )


def test_chat_memory_is_model_selected_and_persistent(tmp_path, monkeypatch):
    client, container, fake = _make_client(tmp_path, monkeypatch)

    save = _chat(client, "user-A", "این اطلاعات رو ذخیره کن: پایتون زبان خوبی هست. من پایتون را دوست دارم.", "memory-write-session")
    assert save.status_code == 200, save.text
    assert save.json()["status"] == "completed"
    assert save.json()["tools_used"] is True

    scope_a = MemoryScope(owner_id="user-A", conversation_id="memory-write-session")
    memories_a = list(container.memory_repository.list_memories(scope=scope_a))
    assert len(memories_a) == 1
    assert memories_a[0].content == "پایتون زبان خوبی هست. من پایتون را دوست دارم."
    assert "ذخیره کن" not in memories_a[0].content

    search = _chat(client, "user-A", "من چه زبان برنامه‌نویسی‌ای را دوست دارم؟", "memory-search-new-session")
    assert search.status_code == 200, search.text
    assert search.json()["status"] == "completed"
    assert search.json()["tools_used"] is True
    assert "پایتون" in search.json()["answer"]

    assistant_tool_calls = []
    for request in fake.calls:
        for message in request.messages:
            if message.get("role") == "assistant":
                assistant_tool_calls.extend(message.get("tool_calls") or [])
    names = [call.get("function", {}).get("name") for call in assistant_tool_calls]
    assert "memory.write" in names
    assert "memory.search" in names
    assert isinstance(container.agentic_llm_provider, AgenticLLMProvider)


def test_chat_memory_isolation_between_principals(tmp_path, monkeypatch):
    client, container, _ = _make_client(tmp_path, monkeypatch)

    save = _chat(client, "user-A", "این اطلاعات رو ذخیره کن: پایتون زبان خوبی هست. من پایتون را دوست دارم.", "a-write")
    assert save.status_code == 200, save.text

    search_a = _chat(client, "user-A", "من چه زبان برنامه‌نویسی‌ای را دوست دارم؟", "a-search")
    assert search_a.status_code == 200, search_a.text
    assert "پایتون" in search_a.json()["answer"]

    search_b = _chat(client, "user-B", "من چه زبان برنامه‌نویسی‌ای را دوست دارم؟", "b-search")
    assert search_b.status_code == 200, search_b.text
    assert "پایتون" not in search_b.json()["answer"]
    assert search_b.json()["answer"] == "اطلاعاتی پیدا نشد."

    scope_b = MemoryScope(owner_id="user-B", conversation_id="b-search")
    assert list(container.memory_repository.list_memories(scope=scope_b)) == []


def test_chat_rejects_missing_trusted_principal(tmp_path, monkeypatch):
    client, _, _ = _make_client(tmp_path, monkeypatch)
    response = client.post(
        "/v1/chat",
        json={"message": "سلام", "conversation_id": "anonymous-session"},
    )
    assert response.status_code == 401
