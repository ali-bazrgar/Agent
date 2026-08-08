from __future__ import annotations

from superagent.config.settings import Settings
from superagent.core.errors import ProviderError
from superagent.infrastructure.http_client import ProviderHttpClient
from superagent.providers.contracts import LLMProvider, LLMRequest, LLMResponse, ProviderCapabilities, ProviderHealth, ProviderHealthStatus


class LlamaCppLLMProvider(LLMProvider):
    """HTTP provider for llama.cpp OpenAI-compatible chat completions."""

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

    def complete(self, request: LLMRequest) -> LLMResponse:
        payload: dict[str, object] = {
            "messages": [{"role": "user", "content": request.prompt}],
            "stream": False,
        }
        if request.system_prompt:
            payload["messages"] = [
                {"role": "system", "content": request.system_prompt},
                {"role": "user", "content": request.prompt},
            ]
        if self.settings.llm_model_id:
            payload["model"] = self.settings.llm_model_id
        if request.max_tokens is not None:
            payload["max_tokens"] = request.max_tokens
        if request.temperature is not None:
            payload["temperature"] = request.temperature
        try:
            response_payload = self.client.request_json("POST", "/v1/chat/completions", json_body=payload)
        except ProviderError:
            raise
        text = self._extract_text(response_payload)
        return LLMResponse(
            text=text,
            model_id=self._extract_model_id(response_payload),
            token_usage=self._extract_token_usage(response_payload),
            provider_name="llama.cpp",
            finish_reason=self._extract_finish_reason(response_payload),
        )

    def check_health(self) -> ProviderHealth:
        try:
            payload = self.client.request_json("GET", "/health")
        except ProviderError as exc:
            return ProviderHealth(name="llm", status=ProviderHealthStatus.UNAVAILABLE, message=str(exc))
        if isinstance(payload, dict) and payload.get("status") in {"ok", "healthy"}:
            return ProviderHealth(name="llm", status=ProviderHealthStatus.HEALTHY, message="provider responded healthy")
        return ProviderHealth(name="llm", status=ProviderHealthStatus.UNAVAILABLE, message="provider health response was malformed")

    def capabilities(self) -> ProviderCapabilities:
        return ProviderCapabilities(chat=True, streaming=True, structured_output=True)

    def close(self) -> None:
        self.client.close()

    def _extract_text(self, payload: dict[str, object]) -> str:
        choices = payload.get("choices")
        if isinstance(choices, list) and choices:
            first_choice = choices[0]
            if isinstance(first_choice, dict):
                message = first_choice.get("message")
                if isinstance(message, dict):
                    content = message.get("content")
                    if isinstance(content, str):
                        return content
                    if isinstance(content, list):
                        parts = []
                        for part in content:
                            if isinstance(part, dict) and isinstance(part.get("text"), str):
                                parts.append(part["text"])
                        if parts:
                            return "".join(parts)
                if isinstance(first_choice.get("text"), str):
                    return first_choice["text"]
        if isinstance(payload.get("text"), str):
            return payload["text"]
        if isinstance(payload.get("content"), str):
            return payload["content"]
        raise ProviderError("provider returned a malformed chat response", provider_name="llm", operation="complete", retryable=False)

    def _extract_model_id(self, payload: dict[str, object]) -> str | None:
        model = payload.get("model")
        if isinstance(model, str):
            return model
        return self.settings.llm_model_id

    def _extract_token_usage(self, payload: dict[str, object]) -> int | None:
        usage = payload.get("usage")
        if isinstance(usage, dict):
            total_tokens = usage.get("total_tokens")
            if isinstance(total_tokens, int):
                return total_tokens
        return None

    def _extract_finish_reason(self, payload: dict[str, object]) -> str | None:
        choices = payload.get("choices")
        if isinstance(choices, list) and choices:
            first_choice = choices[0]
            if isinstance(first_choice, dict):
                finish_reason = first_choice.get("finish_reason")
                if isinstance(finish_reason, str):
                    return finish_reason
        return None
