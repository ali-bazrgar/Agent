from __future__ import annotations

from typing import Any

from superagent.config.settings import Settings
from superagent.core.errors import ProviderError
from superagent.infrastructure.http_client import ProviderHttpClient


class OpenAICompatibleModelDiscovery:
    """Discover model identifiers from an OpenAI-compatible /v1/models endpoint."""

    def __init__(self, settings: Settings, client: ProviderHttpClient | None = None) -> None:
        self.settings = settings
        self.client = client or ProviderHttpClient(
            base_url=settings.llm_base_url,
            connect_timeout=settings.provider_connect_timeout_seconds,
            read_timeout=settings.provider_read_timeout_seconds,
            total_timeout=settings.provider_total_timeout_seconds,
            retry_count=settings.provider_retry_count,
            retry_backoff_seconds=settings.provider_retry_backoff_seconds,
            provider_name="llm",
            api_key=settings.provider_api_key,
        )
        self._owns_client = client is None

    def list_models(self) -> list[dict[str, Any]]:
        payload = self.client.request_json("GET", "/v1/models")
        data = payload.get("data")
        if not isinstance(data, list):
            raise ProviderError(
                "provider returned malformed model discovery response",
                provider_name="llm",
                operation="list_models",
                retryable=False,
            )
        return [item for item in data if isinstance(item, dict)]

    def model_ids(self) -> list[str]:
        result: list[str] = []
        for item in self.list_models():
            model_id = item.get("id")
            if isinstance(model_id, str) and model_id.strip():
                result.append(model_id.strip())
        return result

    def close(self) -> None:
        if self._owns_client:
            self.client.close()
