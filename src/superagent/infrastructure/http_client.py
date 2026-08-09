from __future__ import annotations

import json
import time
from collections.abc import Iterator
from typing import Any

import httpx

from superagent.core.errors import ProviderError


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
        self.base_url = base_url.rstrip("/")
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

    def stream_sse(
        self,
        method: str,
        path: str,
        *,
        json_body: dict[str, Any] | None = None,
        headers: dict[str, str] | None = None,
    ) -> Iterator[str]:
        """Yield SSE data payloads from a long-lived provider response."""
        try:
            with self._client.stream(method, path, json=json_body, headers=headers) as response:
                if response.status_code >= 400:
                    raise ProviderError(
                        f"provider returned HTTP {response.status_code}",
                        provider_name=self.provider_name,
                        operation=f"{method} {path}",
                        status_code=response.status_code,
                        retryable=response.status_code >= 500,
                    )
                data_lines: list[str] = []
                for line in response.iter_lines():
                    if line == "":
                        if data_lines:
                            yield "\n".join(data_lines)
                            data_lines = []
                        continue
                    if line.startswith(":"):
                        continue
                    if line.startswith("data:"):
                        data_lines.append(line[5:].lstrip())
                if data_lines:
                    yield "\n".join(data_lines)
        except ProviderError:
            raise
        except httpx.TimeoutException as exc:
            raise ProviderError(
                "provider streaming request timed out",
                provider_name=self.provider_name,
                operation=f"{method} {path}",
                retryable=True,
            ) from exc
        except httpx.ConnectError as exc:
            raise ProviderError(
                "provider streaming connection failed",
                provider_name=self.provider_name,
                operation=f"{method} {path}",
                retryable=True,
            ) from exc
        except httpx.HTTPError as exc:
            raise ProviderError(
                "provider streaming request failed",
                provider_name=self.provider_name,
                operation=f"{method} {path}",
                retryable=False,
            ) from exc

    @staticmethod
    def parse_sse_json(data: str, *, provider_name: str, operation: str) -> dict[str, Any] | None:
        if data.strip() == "[DONE]":
            return None
        try:
            payload = json.loads(data)
        except json.JSONDecodeError as exc:
            raise ProviderError(
                "provider returned malformed SSE JSON",
                provider_name=provider_name,
                operation=operation,
                retryable=False,
            ) from exc
        if not isinstance(payload, dict):
            raise ProviderError(
                "provider returned an unexpected SSE payload shape",
                provider_name=provider_name,
                operation=operation,
                retryable=False,
            )
        return payload

    def close(self) -> None:
        self._client.close()
