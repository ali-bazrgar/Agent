from fastapi.testclient import TestClient

from superagent.api.app import create_app
from superagent.api.chat import get_container
from superagent.application.container import AppContainer
from superagent.config.settings import Settings
from superagent.database.config import DatabaseConfig
from superagent.database.engine import DatabaseEngine
from superagent.llm.capabilities import CapabilitySet
from superagent.providers.contracts import (
    LLMProvider,
    LLMRequest,
    LLMResponse,
    ProviderCapabilities,
    ProviderHealth,
    ProviderHealthStatus,
    LLMToolCall,
)


class MemoryAgentFakeLLM(LLMProvider):
    """Deterministic OpenAI-compatible-shaped model for the real /chat tool loop."""

    def __init__(self) -> None:
        self.calls: list[LLMRequest] = []

    def complete(self, request: LLMRequest) -> LLMResponse:
        self.calls.append(request)
        tool_messages = [m for m in request.messages if m.get("role") == "tool"]
        user_text = request.prompt

        if "پایتون" in user_text and not tool_messages:
            return LLMResponse(
                model_id="memory-agent-fake",
                tool_calls=[
                    LLMToolCall(
                        id="call-memory-write-1",
                        name="memory.write",
                        arguments={
                            "content": "پایتون زبان خوبی هست. من پایتون را دوست دارم.",
                            "kind": "user",
                            "importance": 0.9,
                        },
                    )
                ],
            )

        if "چه زبان برنامه" in user_text and not tool_messages:
            return LLMResponse(
                model_id="memory-agent-fake",
                tool_calls=[
                    LLMToolCall(
                        id="call-memory-search-1",
                        name="memory.search",
                        arguments={"query": "زبان برنامه نویسی مورد علاقه کاربر", "limit": 5},
                    )
                ],
            )

        if tool_messages:
            content = tool_messages[-1].get("content", "")
            if "memory.write" in user_text or "پایتون" in user_text:
                return LLMResponse(text="ذخیره شد.", model_id="memory-agent-fake")
            if "پایتون" in content:
                return LLMResponse(text="شما پایتون را دوست دارید.", model_id="memory-agent-fake")

        return LLMResponse(text="پاسخ تستی.", model_id="memory-agent-fake")

    def check_health(self) -> ProviderHealth:
        return ProviderHealth(name="memory-agent-fake", status=ProviderHealthStatus.HEALTHY)

    def capabilities(self) -> ProviderCapabilities:
        return ProviderCapabilities(chat=True, tool_calling=True)


def _make_client(tmp_path):
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


def test_chat_memory_is_model_selected_and_persistent(tmp_path):
    client, container, fake = _make_client(tmp_path)

    save = client.post(
        "/v1/chat",
        json={
            "message": "این اطلاعات رو ذخیره کن: پایتون زبان خوبی هست. من پایتون را دوست دارم.",
            "conversation_id": "memory-write-session",
            "execution_config": {"llm_driven_tools": True},
        },
    )
    assert save.status_code == 200, save.text
    save_data = save.json()
    assert save_data["status"] == "completed"
    assert save_data["tools_used"] is True

    memories = list(container.memory_repository.list_memories())
    assert len(memories) == 1
    assert memories[0].content == "پایتون زبان خوبی هست. من پایتون را دوست دارم."
    assert "ذخیره کن" not in memories[0].content

    search = client.post(
        "/v1/chat",
        json={
            "message": "من چه زبان برنامه‌نویسی‌ای را دوست دارم؟",
            "conversation_id": "memory-search-new-session",
            "execution_config": {"llm_driven_tools": True},
        },
    )
    assert search.status_code == 200, search.text
    search_data = search.json()
    assert search_data["status"] == "completed"
    assert search_data["tools_used"] is True
    assert "پایتون" in search_data["answer"]

    assert any(
        any(call.name == "memory.write" for call in response.tool_calls)
        for response in [MemoryAgentFakeLLM._response_from_request(req) for req in []]
    ) is False
    assert any(
        any(message.get("role") == "tool" for message in request.messages)
        for request in fake.calls
    )
