from __future__ import annotations

import json

from superagent.config.settings import Settings
from superagent.core.errors import ProviderError
from superagent.infrastructure.http_client import ProviderHttpClient
from superagent.providers.contracts import (
    LLMProvider,
    LLMRequest,
    LLMResponse,
    LLMToolCall,
    ProviderCapabilities,
    ProviderHealth,
    ProviderHealthStatus,
)


class OpenAICompatibleLLMProvider(LLMProvider):
    """Provider-neutral HTTP adapter for OpenAI-compatible chat APIs."""

    provider_name = "openai-compatible"

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
        messages = list(request.messages)
        if not messages:
            if request.system_prompt:
                messages.append({"role": "system", "content": request.system_prompt})
            messages.append({"role": "user", "content": request.prompt})

        payload: dict[str, object] = {"messages": messages, "stream": False}
        if self.settings.llm_model_id:
            payload["model"] = self.settings.llm_model_id
        if request.tools:
            payload["tools"] = request.tools
            payload["tool_choice"] = request.tool_choice
        if request.max_tokens is not None:
            payload["max_tokens"] = request.max_tokens
        elif self.settings.llm_max_output_tokens is not None:
            payload["max_tokens"] = self.settings.llm_max_output_tokens
        if request.temperature is not None:
            payload["temperature"] = request.temperature
        else:
            payload["temperature"] = self.settings.llm_temperature

        try:
            response_payload = self.client.request_json(
                "POST", self.settings.llm_chat_completions_path, json_body=payload
            )
        except ProviderError:
            raise

        return LLMResponse(
            text=self._extract_text(response_payload),
            model_id=self._extract_model_id(response_payload),
            token_usage=self._extract_token_usage(response_payload),
            provider_name=self.provider_name,
            finish_reason=self._extract_finish_reason(response_payload),
            tool_calls=self._extract_tool_calls(response_payload),
        )

    def check_health(self) -> ProviderHealth:
        try:
            self.client.request_json("GET", self.settings.llm_health_path)
        except ProviderError as exc:
            return ProviderHealth(name="llm", status=ProviderHealthStatus.UNAVAILABLE, message=str(exc))
        return ProviderHealth(name="llm", status=ProviderHealthStatus.HEALTHY, message="provider responded")

    def capabilities(self) -> ProviderCapabilities:
        return ProviderCapabilities(
            chat=True,
            streaming=True,
            structured_output=True,
            tool_calling=True,
            context_window_tokens=self.settings.context_window_tokens,
            max_output_tokens=self.settings.llm_max_output_tokens,
        )

    def close(self) -> None:
        self.client.close()

    def _first_choice(self, payload: dict[str, object]) -> dict[str, object] | None:
        choices = payload.get("choices")
        if isinstance(choices, list) and choices and isinstance(choices[0], dict):
            return choices[0]
        return None

    def _extract_text(self, payload: dict[str, object]) -> str:
        first_choice = self._first_choice(payload)
        if first_choice:
            message = first_choice.get("message")
            if isinstance(message, dict):
                content = message.get("content")
                if isinstance(content, str):
                    return content
                if isinstance(content, list):
                    parts = [
                        part.get("text", "")
                        for part in content
                        if isinstance(part, dict) and isinstance(part.get("text"), str)
                    ]
                    if parts:
                        return "".join(parts)
        if isinstance(payload.get("text"), str):
            return payload["text"]
        if isinstance(payload.get("content"), str):
            return payload["content"]
        if self._extract_tool_calls(payload):
            return ""
        raise ProviderError(
            "provider returned a malformed chat response",
            provider_name="llm",
            operation="complete",
            retryable=False,
        )

    def _extract_tool_calls(self, payload: dict[str, object]) -> list[LLMToolCall]:
        first_choice = self._first_choice(payload)
        if not first_choice:
            return []
        message = first_choice.get("message")
        if not isinstance(message, dict):
            return []
        raw_calls = message.get("tool_calls")
        if not isinstance(raw_calls, list):
            return []
        calls: list[LLMToolCall] = []
        for index, raw in enumerate(raw_calls):
            if not isinstance(raw, dict):
                continue
            function = raw.get("function")
            if not isinstance(function, dict):
                continue
            name = function.get("name")
            if not isinstance(name, str) or not name.strip():
                continue
            arguments = function.get("arguments", {})
            if isinstance(arguments, str):
                try:
                    arguments = json.loads(arguments)
                except json.JSONDecodeError as exc:
                    raise ProviderError(
                        f"tool '{name}' returned invalid JSON arguments: {exc}",
                        provider_name="llm",
                        operation="complete",
                        retryable=False,
                    ) from exc
            if not isinstance(arguments, dict):
                raise ProviderError(
                    f"tool '{name}' returned non-object arguments",
                    provider_name="llm",
                    operation="complete",
                    retryable=False,
                )
            call_id = raw.get("id")
            if not isinstance(call_id, str) or not call_id:
                call_id = f"llm-call-{index + 1}"
            calls.append(LLMToolCall(id=call_id, name=name.strip(), arguments=arguments))
        return calls

    def _extract_model_id(self, payload: dict[str, object]) -> str | None:
        model = payload.get("model")
        return model if isinstance(model, str) else self.settings.llm_model_id

    def _extract_token_usage(self, payload: dict[str, object]) -> int | None:
        usage = payload.get("usage")
        if isinstance(usage, dict) and isinstance(usage.get("total_tokens"), int):
            return usage["total_tokens"]
        return None

    def _extract_finish_reason(self, payload: dict[str, object]) -> str | None:
        first_choice = self._first_choice(payload)
        if first_choice:
            reason = first_choice.get("finish_reason")
            return reason if isinstance(reason, str) else None
        return None
