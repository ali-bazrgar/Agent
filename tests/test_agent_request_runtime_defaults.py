from __future__ import annotations

from superagent.agents.models import AgentRequest
from superagent.config.settings import Settings


def test_agent_request_uses_application_runtime_defaults(monkeypatch) -> None:
    settings = Settings(
        context_window_tokens=16384,
        llm_max_output_tokens=2048,
        llm_temperature=0.2,
        llm_top_p=0.9,
    )
    monkeypatch.setattr("superagent.config.settings.get_settings", lambda: settings)

    request = AgentRequest(
        request_id="req-1",
        conversation_id="conv-1",
        message="hello",
    )

    assert request.execution_config["context_window_tokens"] == 16384
    assert request.execution_config["max_tokens"] == 2048
    assert request.execution_config["temperature"] == 0.2
    assert request.execution_config["top_p"] == 0.9


def test_explicit_request_overrides_remain_authoritative(monkeypatch) -> None:
    settings = Settings(context_window_tokens=16384, llm_max_output_tokens=2048)
    monkeypatch.setattr("superagent.config.settings.get_settings", lambda: settings)

    request = AgentRequest(
        request_id="req-2",
        conversation_id="conv-2",
        message="hello",
        execution_config={
            "context_window_tokens": 8192,
            "max_tokens": 512,
            "temperature": 0.0,
        },
    )

    assert request.execution_config["context_window_tokens"] == 8192
    assert request.execution_config["max_tokens"] == 512
    assert request.execution_config["temperature"] == 0.0
