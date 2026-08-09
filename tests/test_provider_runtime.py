from __future__ import annotations

import httpx

from superagent.config.settings import Settings
from superagent.infrastructure.http_client import ProviderHttpClient
from superagent.llm.llama_cpp_provider import LlamaCppLLMProvider
from superagent.providers.contracts import ProviderHealthStatus, RerankRequest


def _settings() -> Settings:
    return Settings(_env_file=None)


def test_provider_configuration_defaults_are_applied() -> None:
    settings = Settings(_env_file=None)
    assert settings.llm_provider == "openai_compatible"
    assert settings.llm_base_url.startswith("http")
    assert settings.llm_chat_completions_path == "/v1/chat/completions"
    assert settings.llm_temperature == 0.7
    # None intentionally means no application-side output ceiling. Runtime/model
    # capabilities remain responsible for the effective maximum.
    assert settings.llm_max_output_tokens is None
    assert settings.context_window_tokens >= 256


def test_provider_health_reports_unavailable_for_malformed_payload() -> None:
    transport = httpx.MockTransport(lambda request: httpx.Response(200, json={"status": "unknown"}))
    client = ProviderHttpClient(base_url="http://example.invalid", connect_timeout=0.1, read_timeout=0.1, total_timeout=0.1, retry_count=0, retry_backoff_seconds=0.0, provider_name="llm", transport=transport)
    provider = LlamaCppLLMProvider(_settings(), client=client)
    health = provider.check_health()
    assert health.status == ProviderHealthStatus.UNAVAILABLE


def test_rerank_request_accepts_top_n() -> None:
    request = RerankRequest(query="why", candidates=["alpha", "beta"], top_n=1)
    assert request.top_n == 1
