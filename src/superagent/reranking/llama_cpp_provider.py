from __future__ import annotations

from superagent.config.settings import Settings
from superagent.core.errors import ProviderError
from superagent.infrastructure.http_client import ProviderHttpClient
from superagent.providers.contracts import ProviderCapabilities, ProviderHealth, ProviderHealthStatus, RerankerProvider, RerankRequest, RerankResponse


class LlamaCppRerankerProvider(RerankerProvider):
    """HTTP provider for llama.cpp reranking with explicit request controls."""

    def __init__(self, settings: Settings, client: ProviderHttpClient | None = None) -> None:
        self.settings = settings
        self.client = client or ProviderHttpClient(base_url=settings.reranker_base_url, connect_timeout=settings.provider_connect_timeout_seconds, read_timeout=settings.provider_read_timeout_seconds, total_timeout=settings.provider_total_timeout_seconds, retry_count=settings.provider_retry_count, retry_backoff_seconds=settings.provider_retry_backoff_seconds, provider_name="reranker", api_key=settings.provider_api_key)

    def rerank(self, request: RerankRequest) -> RerankResponse:
        if not request.candidates:
            raise ProviderError("rerank request requires at least one candidate", provider_name="reranker", operation="rerank", retryable=False)
        top_n = request.top_n or len(request.candidates)
        payload: dict[str, object] = {"query": request.query, "documents": request.candidates, "top_n": min(top_n, len(request.candidates))}
        model_id = request.model or self.settings.reranker_model_id
        if model_id:
            payload["model"] = model_id
        if request.return_documents is not None:
            payload["return_documents"] = request.return_documents
        try:
            response_payload = self.client.request_json("POST", "/v1/rerank", json_body=payload)
        except ProviderError:
            raise
        ranked_items = self._extract_ranked_items(response_payload, request.candidates)
        return RerankResponse(ranked_items=ranked_items[:top_n], provider_name="llama.cpp", model_id=model_id)

    def check_health(self) -> ProviderHealth:
        try:
            payload = self.client.request_json("GET", "/health")
        except ProviderError as exc:
            return ProviderHealth(name="reranker", status=ProviderHealthStatus.UNAVAILABLE, message=str(exc))
        if isinstance(payload, dict) and payload.get("status") in {"ok", "healthy"}:
            return ProviderHealth(name="reranker", status=ProviderHealthStatus.HEALTHY, message="provider responded healthy")
        return ProviderHealth(name="reranker", status=ProviderHealthStatus.UNAVAILABLE, message="provider health response was malformed")

    def capabilities(self) -> ProviderCapabilities:
        return ProviderCapabilities(reranking=True)

    def close(self) -> None:
        self.client.close()

    def _extract_ranked_items(self, payload: dict[str, object], candidates: list[str]) -> list[dict[str, object]]:
        results = payload.get("results")
        if isinstance(results, list):
            ranked_items: list[dict[str, object]] = []
            for index, item in enumerate(results):
                if not isinstance(item, dict):
                    continue
                score = item.get("score")
                parsed_score = float(score) if isinstance(score, (int, float)) else None
                if parsed_score is None and isinstance(item.get("relevance_score"), (int, float)):
                    parsed_score = float(item["relevance_score"])
                document_text = item.get("document")
                if document_text is None and index < len(candidates):
                    document_text = candidates[index]
                if parsed_score is None:
                    continue
                ranked_items.append({"text": document_text if document_text is not None else candidates[index] if index < len(candidates) else "", "score": parsed_score, "index": item.get("index", index)})
            if ranked_items:
                ranked_items.sort(key=lambda item: item["score"], reverse=True)
                return ranked_items
        raise ProviderError("provider returned a malformed rerank response", provider_name="reranker", operation="rerank", retryable=False)
