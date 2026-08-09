from __future__ import annotations

import json
import httpx

from superagent.config.settings import Settings
from superagent.embeddings.llama_cpp_provider import LlamaCppEmbeddingProvider
from superagent.infrastructure.http_client import ProviderHttpClient
from superagent.providers.contracts import EmbeddingRequest, RerankRequest
from superagent.reranking.llama_cpp_provider import LlamaCppRerankerProvider


def _settings() -> Settings:
    return Settings(_env_file=None, embedding_base_url="http://example.invalid", reranker_base_url="http://example.invalid", llm_base_url="http://example.invalid", provider_retry_count=0)


def _client(transport: httpx.BaseTransport, name: str) -> ProviderHttpClient:
    return ProviderHttpClient(base_url="http://example.invalid", connect_timeout=0.1, read_timeout=0.1, total_timeout=0.1, retry_count=0, retry_backoff_seconds=0.0, provider_name=name, transport=transport)


def test_embedding_request_overrides_model_and_dimensions() -> None:
    captured: dict[str, object] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured.update(json.loads(request.content))
        return httpx.Response(200, json={"data": [{"embedding": [0.1, 0.2]}]})

    provider = LlamaCppEmbeddingProvider(_settings(), client=_client(httpx.MockTransport(handler), "embedding"))
    response = provider.embed(EmbeddingRequest(texts=["hello"], model="embed-v2", dimensions=2, encoding_format="float"))

    assert captured["model"] == "embed-v2"
    assert captured["dimensions"] == 2
    assert captured["encoding_format"] == "float"
    assert response.model_id == "embed-v2"


def test_rerank_request_overrides_model_and_top_n() -> None:
    captured: dict[str, object] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured.update(json.loads(request.content))
        return httpx.Response(200, json={"results": [{"index": 0, "score": 0.9}, {"index": 1, "score": 0.2}]})

    provider = LlamaCppRerankerProvider(_settings(), client=_client(httpx.MockTransport(handler), "reranker"))
    response = provider.rerank(RerankRequest(query="q", candidates=["a", "b"], model="rerank-v2", top_n=1, return_documents=True))

    assert captured["model"] == "rerank-v2"
    assert captured["top_n"] == 1
    assert captured["return_documents"] is True
    assert response.model_id == "rerank-v2"
    assert len(response.ranked_items) == 1
