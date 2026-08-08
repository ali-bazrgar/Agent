from __future__ import annotations

from superagent.providers.contracts import (
    EmbeddingProvider,
    EmbeddingRequest,
    EmbeddingResponse,
    LLMProvider,
    LLMRequest,
    LLMResponse,
    ProviderCapabilities,
    ProviderHealth,
    ProviderHealthStatus,
    RerankerProvider,
    RerankRequest,
    RerankResponse,
    WebResearchProvider,
    WebResearchRequest,
    WebResearchResponse,
)


class FakeLLMProvider(LLMProvider):
    def complete(self, request: LLMRequest) -> LLMResponse:
        return LLMResponse(text=f"handled:{request.prompt}", provider_name="fake")

    def check_health(self) -> ProviderHealth:
        return ProviderHealth(name="fake", status=ProviderHealthStatus.HEALTHY)

    def capabilities(self) -> ProviderCapabilities:
        return ProviderCapabilities(chat=True)


class FakeEmbeddingProvider(EmbeddingProvider):
    def embed(self, request: EmbeddingRequest) -> EmbeddingResponse:
        return EmbeddingResponse(embeddings=[[1.0, 2.0]], provider_name="fake")

    def check_health(self) -> ProviderHealth:
        return ProviderHealth(name="fake", status=ProviderHealthStatus.HEALTHY)

    def capabilities(self) -> ProviderCapabilities:
        return ProviderCapabilities(embedding=True, batch_embedding=True)


class FakeRerankerProvider(RerankerProvider):
    def rerank(self, request: RerankRequest) -> RerankResponse:
        return RerankResponse(ranked_items=[{"text": request.candidates[0], "score": 1.0}], provider_name="fake")

    def check_health(self) -> ProviderHealth:
        return ProviderHealth(name="fake", status=ProviderHealthStatus.HEALTHY)

    def capabilities(self) -> ProviderCapabilities:
        return ProviderCapabilities(reranking=True)


class FakeWebProvider(WebResearchProvider):
    def search(self, request: WebResearchRequest) -> WebResearchResponse:
        return WebResearchResponse(results=[{"title": request.query, "url": "https://example.invalid"}], provider_name="fake")


def test_provider_contracts_are_implemented_by_fakes() -> None:
    assert FakeLLMProvider().complete(LLMRequest(prompt="hi")).text == "handled:hi"
    assert FakeEmbeddingProvider().embed(EmbeddingRequest(texts=["hi"])).embeddings[0][0] == 1.0
    assert FakeRerankerProvider().rerank(RerankRequest(query="x", candidates=["one"])).ranked_items[0]["score"] == 1.0
    assert FakeWebProvider().search(WebResearchRequest(query="news")).results[0]["title"] == "news"
