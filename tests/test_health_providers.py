from __future__ import annotations

from fastapi.testclient import TestClient

from superagent.api.app import create_app
from superagent.api.health import get_container
from superagent.application.container import AppContainer
from superagent.providers.contracts import (
    EmbeddingProvider,
    EmbeddingRequest,
    EmbeddingResponse,
    LLMProvider,
    LLMRequest,
    LLMResponse,
    ProviderHealth,
    ProviderHealthStatus,
    RerankerProvider,
    RerankRequest,
    RerankResponse,
)


class MockLLM(LLMProvider):
    def __init__(self, healthy: bool = True, raise_exception: bool = False) -> None:
        self.healthy = healthy
        self.raise_exception = raise_exception

    def complete(self, request: LLMRequest) -> LLMResponse:
        return LLMResponse(text="response")

    def check_health(self) -> ProviderHealth:
        if self.raise_exception:
            raise RuntimeError("LLM connection crashed")
        return ProviderHealth(
            name="mock_llm",
            status=ProviderHealthStatus.HEALTHY if self.healthy else ProviderHealthStatus.UNAVAILABLE,
            message="healthy" if self.healthy else "down",
        )

    def capabilities(self) -> ProviderCapabilities:
        return ProviderCapabilities(chat=True)


class MockEmbedding(EmbeddingProvider):
    def __init__(self, healthy: bool = True) -> None:
        self.healthy = healthy

    def embed(self, request: EmbeddingRequest) -> EmbeddingResponse:
        return EmbeddingResponse(embeddings=[])

    def check_health(self) -> ProviderHealth:
        return ProviderHealth(
            name="mock_embedding",
            status=ProviderHealthStatus.HEALTHY if self.healthy else ProviderHealthStatus.UNAVAILABLE,
            message="healthy" if self.healthy else "down",
        )

    def capabilities(self) -> ProviderCapabilities:
        return ProviderCapabilities(embedding=True)


class MockReranker(RerankerProvider):
    def __init__(self, healthy: bool = True) -> None:
        self.healthy = healthy

    def rerank(self, request: RerankRequest) -> RerankResponse:
        return RerankResponse(ranked_items=[])

    def check_health(self) -> ProviderHealth:
        return ProviderHealth(
            name="mock_reranker",
            status=ProviderHealthStatus.HEALTHY if self.healthy else ProviderHealthStatus.UNAVAILABLE,
            message="healthy" if self.healthy else "down",
        )

    def capabilities(self) -> ProviderCapabilities:
        return ProviderCapabilities(reranking=True)


def _build_test_container(
    llm_healthy: bool = True,
    emb_healthy: bool = True,
    rerank_healthy: bool = True,
    llm_crashes: bool = False,
) -> AppContainer:
    return AppContainer(
        llm_provider=MockLLM(healthy=llm_healthy, raise_exception=llm_crashes),
        embedding_provider=MockEmbedding(healthy=emb_healthy),
        reranker_provider=MockReranker(healthy=rerank_healthy),
    )


def test_health_all_providers_healthy() -> None:
    app = create_app()
    container = _build_test_container(True, True, True)
    app.dependency_overrides[get_container] = lambda: container

    client = TestClient(app)
    response = client.get("/api/v1/health")

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert data["providers"]["llm"]["status"] == "healthy"
    assert data["providers"]["embedding"]["status"] == "healthy"
    assert data["providers"]["reranker"]["status"] == "healthy"


def test_health_llm_unavailable() -> None:
    app = create_app()
    container = _build_test_container(llm_healthy=False, emb_healthy=True, rerank_healthy=True)
    app.dependency_overrides[get_container] = lambda: container

    client = TestClient(app)
    response = client.get("/api/v1/health")

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "degraded"
    assert data["providers"]["llm"]["status"] == "unavailable"
    assert data["providers"]["embedding"]["status"] == "healthy"


def test_health_embedding_unavailable() -> None:
    app = create_app()
    container = _build_test_container(llm_healthy=True, emb_healthy=False, rerank_healthy=True)
    app.dependency_overrides[get_container] = lambda: container

    client = TestClient(app)
    response = client.get("/api/v1/health")

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "degraded"
    assert data["providers"]["embedding"]["status"] == "unavailable"


def test_health_reranker_unavailable() -> None:
    app = create_app()
    container = _build_test_container(llm_healthy=True, emb_healthy=True, rerank_healthy=False)
    app.dependency_overrides[get_container] = lambda: container

    client = TestClient(app)
    response = client.get("/api/v1/health")

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "degraded"
    assert data["providers"]["reranker"]["status"] == "unavailable"


def test_health_multiple_providers_unavailable() -> None:
    app = create_app()
    container = _build_test_container(llm_healthy=False, emb_healthy=False, rerank_healthy=False)
    app.dependency_overrides[get_container] = lambda: container

    client = TestClient(app)
    response = client.get("/api/v1/health")

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "degraded"
    assert data["providers"]["llm"]["status"] == "unavailable"
    assert data["providers"]["embedding"]["status"] == "unavailable"
    assert data["providers"]["reranker"]["status"] == "unavailable"


def test_health_provider_raises_exception() -> None:
    app = create_app()
    container = _build_test_container(llm_healthy=True, emb_healthy=True, rerank_healthy=True, llm_crashes=True)
    app.dependency_overrides[get_container] = lambda: container

    client = TestClient(app)
    response = client.get("/api/v1/health")

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "degraded"
    assert data["providers"]["llm"]["status"] == "unavailable"
    assert "LLM connection crashed" in data["providers"]["llm"]["message"]
