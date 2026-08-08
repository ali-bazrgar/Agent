from __future__ import annotations

import time
from typing import Any

import httpx

from superagent.core.errors import ProviderError


def normalize_provider_base_url(base_url: str) -> str:
    """Normalize provider roots so callers may configure either a server root or API prefix.

    llama.cpp exposes OpenAI-compatible routes below ``/v1``. Some deployments and
    reverse proxies expose the same API below ``/api/v1``. Provider adapters append
    the operation path themselves, so those suffixes must be removed here to avoid
    requests such as ``/v1/v1/chat/completions``.
    """
    value = base_url.strip().rstrip("/")
    for suffix in ("/api/v1", "/v1"):
        if value.lower().endswith(suffix):
            value = value[: -len(suffix)].rstrip("/")
            break
    return value or "http://127.0.0.1"


class ProviderHttpClient:
    """Small reusable HTTP client for provider adapters with retries and timeouts."""

    def __init__(
        self,
        *,
        base_url: str,
        connect_timeout: float,
        read_timeout: float,
        total_timeout: float,
        retry_count: int,
        retry_backoff_seconds: float,
        provider_name: str,
        api_key: str | None = None,
        transport: httpx.BaseTransport | None = None,
    ) -> None:
        self.base_url = normalize_provider_base_url(base_url)
        self.provider_name = provider_name
        self.retry_count = max(0, retry_count)
        self.retry_backoff_seconds = max(0.0, retry_backoff_seconds)
        self._client = httpx.Client(
            base_url=self.base_url,
            timeout=httpx.Timeout(connect=connect_timeout, read=read_timeout, write=10.0, pool=total_timeout),
            limits=httpx.Limits(max_connections=10, max_keepalive_connections=5),
            transport=transport,
            headers={"Authorization": f"Bearer {api_key}"} if api_key else None,
        )

    def request_json(
        self,
        method: str,
        path: str,
        *,
        json_body: dict[str, Any] | None = None,
        headers: dict[str, str] | None = None,
    ) -> dict[str, Any]:
        last_error: Exception | None = None
        for attempt in range(self.retry_count + 1):
            try:
                response = self._client.request(method, path, json=json_body, headers=headers)
                if response.status_code >= 500 and attempt < self.retry_count:
                    time.sleep(self.retry_backoff_seconds * (attempt + 1))
                    continue
                if response.status_code >= 400:
                    raise ProviderError(
                        f"provider returned HTTP {response.status_code}",
                        provider_name=self.provider_name,
                        operation=f"{method} {path}",
                        status_code=response.status_code,
                        retryable=response.status_code >= 500,
                    )
                try:
                    payload = response.json()
                except ValueError as exc:
                    raise ProviderError(
                        "provider returned invalid JSON",
                        provider_name=self.provider_name,
                        operation=f"{method} {path}",
                        status_code=response.status_code,
                        retryable=False,
                    ) from exc
                if not isinstance(payload, dict):
                    raise ProviderError(
                        "provider returned an unexpected payload shape",
                        provider_name=self.provider_name,
                        operation=f"{method} {path}",
                        status_code=response.status_code,
                        retryable=False,
                    )
                return payload
            except httpx.TimeoutException as exc:
                last_error = exc
                if attempt < self.retry_count:
                    time.sleep(self.retry_backoff_seconds * (attempt + 1))
                    continue
                raise ProviderError(
                    "provider request timed out",
                    provider_name=self.provider_name,
                    operation=f"{method} {path}",
                    retryable=True,
                ) from exc
            except httpx.ConnectError as exc:
                last_error = exc
                if attempt < self.retry_count:
                    time.sleep(self.retry_backoff_seconds * (attempt + 1))
                    continue
                raise ProviderError(
                    "provider connection failed",
                    provider_name=self.provider_name,
                    operation=f"{method} {path}",
                    retryable=True,
                ) from exc
            except ProviderError:
                raise
            except httpx.HTTPError as exc:
                last_error = exc
                if attempt < self.retry_count:
                    time.sleep(self.retry_backoff_seconds * (attempt + 1))
                    continue
                raise ProviderError(
                    "provider request failed",
                    provider_name=self.provider_name,
                    operation=f"{method} {path}",
                    retryable=False,
                ) from exc

        if last_error is not None:
            raise ProviderError(
                "provider request failed",
                provider_name=self.provider_name,
                operation="request",
                retryable=False,
            ) from last_error
        raise ProviderError("provider request failed", provider_name=self.provider_name, operation="request", retryable=False)

    def close(self) -> None:
        self._client.close()

    def __enter__(self) -> "ProviderHttpClient":
        return self

    def __exit__(self, exc_type: object, exc_value: object, traceback: object) -> None:
        self.close()
