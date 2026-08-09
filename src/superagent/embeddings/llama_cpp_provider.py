from __future__ import annotations

from superagent.config.settings import Settings
from superagent.core.errors import ProviderError
from superagent.infrastructure.http_client import ProviderHttpClient
from superagent.providers.contracts import EmbeddingProvider, EmbeddingRequest, EmbeddingResponse, ProviderCapabilities, ProviderHealth, ProviderHealthStatus


class LlamaCppEmbeddingProvider(EmbeddingProvider):
    """HTTP provider for llama.cpp embeddings with explicit request controls."""

    def __init__(self, settings: Settings, client: ProviderHttpClient | None = None) -> None:
        self.settings = settings
        self.client = client or ProviderHttpClient(base_url=settings.embedding_base_url, connect_timeout=settings.provider_connect_timeout_seconds, read_timeout=settings.provider_read_timeout_seconds, total_timeout=settings.provider_total_timeout_seconds, retry_count=settings.provider_retry_count, retry_backoff_seconds=settings.provider_retry_backoff_seconds, provider_name="embedding", api_key=settings.provider_api_key)

    def embed(self, request: EmbeddingRequest) -> EmbeddingResponse:
        if not request.texts:
            raise ProviderError("embedding request requires at least one text", provider_name="embedding", operation="embed", retryable=False)
        payload: dict[str, object] = {"input": request.texts}
        model_id = request.model or self.settings.embedding_model_id
        if model_id:
            payload["model"] = model_id
        if request.dimensions is not None:
            payload["dimensions"] = request.dimensions
        if request.encoding_format:
            payload["encoding_format"] = request.encoding_format
        try:
            response_payload = self.client.request_json("POST", "/v1/embeddings", json_body=payload)
        except ProviderError:
            raise
        embeddings = self._extract_embeddings(response_payload)
        return EmbeddingResponse(embeddings=embeddings, provider_name="llama.cpp", model_id=model_id)

    def check_health(self) -> ProviderHealth:
        try:
            payload = self.client.request_json("GET", "/health")
        except ProviderError as exc:
            return ProviderHealth(name="embedding", status=ProviderHealthStatus.UNAVAILABLE, message=str(exc))
        if isinstance(payload, dict) and payload.get("status") in {"ok", "healthy"}:
            return ProviderHealth(name="embedding", status=ProviderHealthStatus.HEALTHY, message="provider responded healthy")
        return ProviderHealth(name="embedding", status=ProviderHealthStatus.UNAVAILABLE, message="provider health response was malformed")

    def capabilities(self) -> ProviderCapabilities:
        return ProviderCapabilities(embedding=True, batch_embedding=True)

    def close(self) -> None:
        self.client.close()

    def _extract_embeddings(self, payload: dict[str, object]) -> list[list[float]]:
        if isinstance(payload.get("data"), list):
            embeddings: list[list[float]] = []
            for item in payload["data"]:
                if isinstance(item, dict) and isinstance(item.get("embedding"), list):
                    values = []
                    for value in item["embedding"]:
                        if isinstance(value, (int, float)):
                            values.append(float(value))
                        else:
                            raise ProviderError("provider returned malformed embedding values", provider_name="embedding", operation="embed", retryable=False)
                    embeddings.append(values)
            if embeddings:
                return embeddings
        if isinstance(payload.get("embeddings"), list):
            embeddings = []
            for item in payload["embeddings"]:
                if isinstance(item, list):
                    values = []
                    for value in item:
                        if isinstance(value, (int, float)):
                            values.append(float(value))
                        else:
                            raise ProviderError("provider returned malformed embedding values", provider_name="embedding", operation="embed", retryable=False)
                    embeddings.append(values)
            if embeddings:
                return embeddings
        raise ProviderError("provider returned a malformed embedding response", provider_name="embedding", operation="embed", retryable=False)
