from __future__ import annotations

import httpx

from superagent.config.settings import Settings
from superagent.embeddings.llama_cpp_provider import LlamaCppEmbeddingProvider
from superagent.llm.llama_cpp_provider import LlamaCppLLMProvider
from superagent.providers.contracts import EmbeddingRequest, LLMRequest, ProviderHealthStatus, RerankRequest
from superagent.reranking.llama_cpp_provider import LlamaCppRerankerProvider
from superagent.infrastructure.http_client import ProviderHttpClient


def _settings() -> Settings:
    return Settings(
        _env_file=None,
        llm_base_url="http://example.invalid",
        embedding_base_url="http://example.invalid",
        reranker_base_url="http://example.invalid",
        provider_connect_timeout_seconds=0.1,
        provider_read_timeout_seconds=0.1,
        provider_total_timeout_seconds=0.1,
        provider_retry_count=0,
        provider_retry_backoff_seconds=0.0,
    )


def test_llm_provider_parses_successful_chat_response() -> None:
    transport = httpx.MockTransport(lambda request: httpx.Response(200, json={"choices": [{"message": {"content": "hello"}}], "model": "mock-model"}))
    client = ProviderHttpClient(base_url="http://example.invalid", connect_timeout=0.1, read_timeout=0.1, total_timeout=0.1, retry_count=0, retry_backoff_seconds=0.0, provider_name="llm", transport=transport)
    provider = LlamaCppLLMProvider(_settings(), client=client)

    response = provider.complete(LLMRequest(prompt="hi"))

    assert response.text == "hello"
    assert response.model_id == "mock-model"


def test_llm_provider_raises_on_malformed_response() -> None:
    transport = httpx.MockTransport(lambda request: httpx.Response(200, json={"choices": []}))
    client = ProviderHttpClient(base_url="http://example.invalid", connect_timeout=0.1, read_timeout=0.1, total_timeout=0.1, retry_count=0, retry_backoff_seconds=0.0, provider_name="llm", transport=transport)
    provider = LlamaCppLLMProvider(_settings(), client=client)

    try:
        provider.complete(LLMRequest(prompt="hi"))
    except Exception as exc:  # pragma: no cover - exercised by tests
        assert "malformed" in str(exc).lower()
    else:
        raise AssertionError("expected malformed response to fail")


def test_llm_provider_retries_transient_errors() -> None:
    attempts = {"count": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        attempts["count"] += 1
        if attempts["count"] == 1:
            return httpx.Response(503, json={"error": "retry"})
        return httpx.Response(200, json={"choices": [{"message": {"content": "retry-ok"}}]})

    transport = httpx.MockTransport(handler)
    client = ProviderHttpClient(base_url="http://example.invalid", connect_timeout=0.1, read_timeout=0.1, total_timeout=0.1, retry_count=1, retry_backoff_seconds=0.0, provider_name="llm", transport=transport)
    provider = LlamaCppLLMProvider(_settings(), client=client)

    response = provider.complete(LLMRequest(prompt="hi"))

    assert response.text == "retry-ok"
    assert attempts["count"] == 2


def test_embedding_provider_embeds_batch() -> None:
    transport = httpx.MockTransport(lambda request: httpx.Response(200, json={"data": [{"embedding": [0.1, 0.2]}, {"embedding": [0.3, 0.4]}]}))
    client = ProviderHttpClient(base_url="http://example.invalid", connect_timeout=0.1, read_timeout=0.1, total_timeout=0.1, retry_count=0, retry_backoff_seconds=0.0, provider_name="embedding", transport=transport)
    provider = LlamaCppEmbeddingProvider(_settings(), client=client)

    response = provider.embed(EmbeddingRequest(texts=["one", "two"]))

    assert response.embeddings == [[0.1, 0.2], [0.3, 0.4]]


def test_reranker_provider_orders_results() -> None:
    transport = httpx.MockTransport(lambda request: httpx.Response(200, json={"results": [{"index": 1, "score": 0.1}, {"index": 0, "score": 0.9}]}))
    client = ProviderHttpClient(base_url="http://example.invalid", connect_timeout=0.1, read_timeout=0.1, total_timeout=0.1, retry_count=0, retry_backoff_seconds=0.0, provider_name="reranker", transport=transport)
    provider = LlamaCppRerankerProvider(_settings(), client=client)

    response = provider.rerank(RerankRequest(query="why", candidates=["alpha", "beta"]))

    assert response.ranked_items[0]["text"] == "beta"
    assert response.ranked_items[0]["score"] == 0.9


def test_provider_health_reports_unavailable_for_malformed_payload() -> None:
    transport = httpx.MockTransport(lambda request: httpx.Response(200, json={"status": "unknown"}))
    client = ProviderHttpClient(base_url="http://example.invalid", connect_timeout=0.1, read_timeout=0.1, total_timeout=0.1, retry_count=0, retry_backoff_seconds=0.0, provider_name="llm", transport=transport)
    provider = LlamaCppLLMProvider(_settings(), client=client)

    health = provider.check_health()

    assert health.status == ProviderHealthStatus.UNAVAILABLE


def test_provider_configuration_defaults_are_applied() -> None:
    settings = Settings(_env_file=None)

    assert settings.llm_base_url.startswith("http")
    assert settings.embedding_base_url.startswith("http")
    assert settings.reranker_base_url.startswith("http")
    assert settings.provider_retry_count >= 0
