from __future__ import annotations

import json
import httpx

from superagent.config.settings import Settings
from superagent.embeddings.llama_cpp_provider import LlamaCppEmbeddingProvider
from superagent.infrastructure.http_client import ProviderHttpClient
from superagent.llm.llama_cpp_provider import LlamaCppLLMProvider
from superagent.llm.openai_compatible_provider import OpenAICompatibleLLMProvider
from superagent.providers.contracts import EmbeddingRequest, LLMRequest, ProviderHealthStatus, RerankRequest
from superagent.reranking.llama_cpp_provider import LlamaCppRerankerProvider


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
        llm_temperature=0.25,
        llm_max_output_tokens=512,
    )


def _client(transport: httpx.BaseTransport) -> ProviderHttpClient:
    return ProviderHttpClient(base_url="http://example.invalid", connect_timeout=0.1, read_timeout=0.1, total_timeout=0.1, retry_count=0, retry_backoff_seconds=0.0, provider_name="llm", transport=transport)


def test_openai_compatible_provider_sends_generation_and_tool_settings() -> None:
    captured: dict[str, object] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured.update(json.loads(request.content))
        return httpx.Response(200, json={"choices": [{"message": {"content": "hello"}}], "model": "mock-model"})

    provider = OpenAICompatibleLLMProvider(_settings(), client=_client(httpx.MockTransport(handler)))
    response = provider.complete(
        LLMRequest(
            prompt="hi",
            tools=[{"type": "function", "function": {"name": "memory.search", "parameters": {"type": "object"}}}],
        )
    )

    assert response.text == "hello"
    assert captured["temperature"] == 0.25
    assert captured["max_tokens"] == 512
    assert captured["tools"]
    assert captured["tool_choice"] == "auto"


def test_openai_compatible_provider_streams_text_and_sets_stream_flag() -> None:
    captured: dict[str, object] = {}
    body = "\n".join([
        'data: {"choices":[{"delta":{"content":"Hel"}}]}',
        '',
        'data: {"choices":[{"delta":{"content":"lo"},"finish_reason":"stop"}]}',
        '',
        'data: [DONE]',
        '',
    ])

    def handler(request: httpx.Request) -> httpx.Response:
        captured.update(json.loads(request.content))
        return httpx.Response(200, text=body, headers={"content-type": "text/event-stream"})

    provider = OpenAICompatibleLLMProvider(_settings(), client=_client(httpx.MockTransport(handler)))
    events = list(provider.stream(LLMRequest(prompt="hi")))

    assert captured["stream"] is True
    assert [event.text_delta for event in events] == ["Hel", "lo"]
    assert events[-1].finish_reason == "stop"


def test_openai_compatible_provider_assembles_streaming_tool_call_arguments() -> None:
    body = "\n".join([
        'data: {"choices":[{"delta":{"tool_calls":[{"index":0,"id":"call-1","function":{"name":"memory.write","arguments":"{\\\"content\\\":\\\"Py"}}]}}]}',
        '',
        'data: {"choices":[{"delta":{"tool_calls":[{"index":0,"function":{"arguments":"thon\\\"}"}}]},"finish_reason":"tool_calls"}]}',
        '',
        'data: [DONE]',
        '',
    ])
    transport = httpx.MockTransport(
        lambda request: httpx.Response(200, text=body, headers={"content-type": "text/event-stream"})
    )
    provider = OpenAICompatibleLLMProvider(_settings(), client=_client(transport))

    events = list(provider.stream(LLMRequest(prompt="save this")))

    assert events[-1].finish_reason == "tool_calls"
    assert events[-1].tool_calls[0].id == "call-1"
    assert events[-1].tool_calls[0].name == "memory.write"
    assert events[-1].tool_calls[0].arguments == {"content": "Python"}


def test_openai_compatible_provider_parses_tool_calls() -> None:
    transport = httpx.MockTransport(
        lambda request: httpx.Response(
            200,
            json={
                "choices": [{
                    "message": {
                        "content": None,
                        "tool_calls": [{"id": "call-1", "type": "function", "function": {"name": "memory.write", "arguments": '{"content":"Python"}'}}],
                    },
                    "finish_reason": "tool_calls",
                }],
                "model": "mock-model",
            },
        )
    )
    provider = OpenAICompatibleLLMProvider(_settings(), client=_client(transport))

    response = provider.complete(LLMRequest(prompt="save this"))

    assert response.text == ""
    assert response.tool_calls[0].name == "memory.write"
    assert response.tool_calls[0].arguments == {"content": "Python"}


def test_llm_provider_parses_successful_chat_response() -> None:
    transport = httpx.MockTransport(lambda request: httpx.Response(200, json={"choices": [{"message": {"content": "hello"}}], "model": "mock-model"}))
    provider = LlamaCppLLMProvider(_settings(), client=_client(transport))

    response = provider.complete(LLMRequest(prompt="hi"))

    assert response.text == "hello"
    assert response.model_id == "mock-model"


def test_llm_provider_raises_on_malformed_response() -> None:
    transport = httpx.MockTransport(lambda request: httpx.Response(200, json={"choices": []}))
    provider = LlamaCppLLMProvider(_settings(), client=_client(transport))

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

    assert settings.llm_provider == "openai_compatible"
    assert settings.llm_base_url.startswith("http")
    assert settings.llm_chat_completions_path == "/v1/chat/completions"
    assert settings.llm_temperature == 0.7
    assert settings.llm_max_output_tokens == 1024
    assert settings.context_window_tokens >= 256
