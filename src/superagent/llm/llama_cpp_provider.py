from __future__ import annotations

import json
from collections import defaultdict
from typing import Iterator

from superagent.config.settings import Settings
from superagent.core.errors import ProviderError
from superagent.infrastructure.http_client import ProviderHttpClient
from superagent.llm.runtime import ModelRuntimeConfig
from superagent.providers.contracts import LLMProvider, LLMRequest, LLMResponse, LLMStreamEvent, LLMToolCall, ProviderCapabilities, ProviderHealth, ProviderHealthStatus


class LlamaCppLLMProvider(LLMProvider):
    """OpenAI-compatible llama.cpp adapter with transparent runtime controls."""

    provider_name = "llama-cpp"

    def __init__(self, settings: Settings, client: ProviderHttpClient | None = None, runtime_config: ModelRuntimeConfig | None = None) -> None:
        self.settings = settings
        self._runtime_config = runtime_config
        self.client = client or ProviderHttpClient(
            base_url=settings.llm_base_url,
            connect_timeout=settings.provider_connect_timeout_seconds,
            read_timeout=settings.provider_read_timeout_seconds,
            total_timeout=settings.provider_total_timeout_seconds,
            retry_count=settings.provider_retry_count,
            retry_backoff_seconds=settings.provider_retry_backoff_seconds,
            provider_name="llama-cpp",
            api_key=settings.provider_api_key,
        )

    def configure_runtime(self, runtime_config: ModelRuntimeConfig) -> None:
        self._runtime_config = runtime_config

    @property
    def runtime_config(self) -> ModelRuntimeConfig | None:
        return self._runtime_config

    def _payload(self, request: LLMRequest, *, stream: bool) -> dict[str, object]:
        messages = list(request.messages)
        if not messages:
            if request.system_prompt:
                messages.append({"role": "system", "content": request.system_prompt})
            messages.append({"role": "user", "content": request.prompt})
        runtime = self._runtime_config
        payload: dict[str, object] = {"messages": messages, "stream": stream}
        model_id = runtime.model_id if runtime is not None else self.settings.llm_model_id
        if model_id:
            payload["model"] = model_id
        if request.tools:
            payload["tools"] = request.tools
            payload["tool_choice"] = request.tool_choice
        max_output = request.max_tokens if request.max_tokens is not None else (runtime.max_output_tokens if runtime is not None else self.settings.llm_max_output_tokens)
        if max_output is not None:
            payload["max_tokens"] = max_output
        payload["temperature"] = request.temperature if request.temperature is not None else (runtime.temperature if runtime is not None else self.settings.llm_temperature)
        payload["top_p"] = request.top_p if request.top_p is not None else (runtime.top_p if runtime is not None else self.settings.llm_top_p)
        payload["frequency_penalty"] = request.frequency_penalty if request.frequency_penalty is not None else self.settings.llm_frequency_penalty
        payload["presence_penalty"] = request.presence_penalty if request.presence_penalty is not None else self.settings.llm_presence_penalty
        if request.seed is not None or self.settings.llm_seed is not None:
            payload["seed"] = request.seed if request.seed is not None else self.settings.llm_seed
        return payload

    def complete(self, request: LLMRequest) -> LLMResponse:
        response_payload = self.client.request_json("POST", self.settings.llm_chat_completions_path, json_body=self._payload(request, stream=False))
        metadata: dict[str, object] = {"timings": self._extract_timings(response_payload)}
        usage = response_payload.get("usage")
        if isinstance(usage, dict):
            metadata["usage"] = usage
        return LLMResponse(text=self._extract_text(response_payload), model_id=self._extract_model_id(response_payload), token_usage=self._extract_token_usage(response_payload), provider_name=self.provider_name, finish_reason=self._extract_finish_reason(response_payload), tool_calls=self._extract_tool_calls(response_payload), metadata=metadata)

    def stream(self, request: LLMRequest) -> Iterator[LLMStreamEvent]:
        """Stream llama.cpp's OpenAI-compatible SSE response without bypassing tool-call events."""
        tool_ids: dict[int, str] = {}
        tool_names: dict[int, str] = {}
        tool_arguments: defaultdict[int, list[str]] = defaultdict(list)
        for data in self.client.stream_sse("POST", self.settings.llm_chat_completions_path, json_body=self._payload(request, stream=True)):
            payload = self.client.parse_sse_json(data, provider_name=self.provider_name, operation="POST stream chat completions")
            if payload is None:
                break
            choices = payload.get("choices")
            if not isinstance(choices, list) or not choices or not isinstance(choices[0], dict):
                continue
            choice = choices[0]
            delta = choice.get("delta") if isinstance(choice.get("delta"), dict) else {}
            text_delta = delta.get("content") if isinstance(delta.get("content"), str) else ""
            raw_tool_calls = delta.get("tool_calls")
            if isinstance(raw_tool_calls, list):
                for raw_call in raw_tool_calls:
                    if not isinstance(raw_call, dict) or not isinstance(raw_call.get("index"), int):
                        continue
                    index = raw_call["index"]
                    if isinstance(raw_call.get("id"), str) and raw_call["id"]:
                        tool_ids[index] = raw_call["id"]
                    function = raw_call.get("function")
                    if isinstance(function, dict):
                        if isinstance(function.get("name"), str) and function["name"]:
                            tool_names[index] = function["name"]
                        if isinstance(function.get("arguments"), str):
                            tool_arguments[index].append(function["arguments"])
            finish_reason = choice.get("finish_reason") if isinstance(choice.get("finish_reason"), str) else None
            completed_tools = self._complete_stream_tools(tool_ids, tool_names, tool_arguments) if finish_reason else []
            metadata: dict[str, object] = {}
            if isinstance(payload.get("model"), str):
                metadata["model_id"] = payload["model"]
            timings = self._extract_timings(payload)
            if timings:
                metadata["timings"] = timings
            usage = payload.get("usage")
            if isinstance(usage, dict):
                metadata["usage"] = usage
            if text_delta or completed_tools or finish_reason is not None or metadata:
                yield LLMStreamEvent(text_delta=text_delta, tool_calls=completed_tools, finish_reason=finish_reason, metadata=metadata)

    def _complete_stream_tools(self, tool_ids: dict[int, str], tool_names: dict[int, str], tool_arguments: defaultdict[int, list[str]]) -> list[LLMToolCall]:
        calls: list[LLMToolCall] = []
        for index in sorted(tool_names):
            name = tool_names[index].strip()
            if not name:
                continue
            raw_arguments = "".join(tool_arguments[index]).strip() or "{}"
            try:
                arguments = json.loads(raw_arguments)
            except json.JSONDecodeError as exc:
                raise ProviderError(f"tool '{name}' returned invalid streaming JSON arguments: {exc}", provider_name=self.provider_name, operation="stream", retryable=False) from exc
            if not isinstance(arguments, dict):
                raise ProviderError(f"tool '{name}' returned non-object streaming arguments", provider_name=self.provider_name, operation="stream", retryable=False)
            calls.append(LLMToolCall(id=tool_ids.get(index, f"llm-stream-call-{index + 1}"), name=name, arguments=arguments))
        return calls

    def check_health(self) -> ProviderHealth:
        try:
            payload = self.client.request_json("GET", self.settings.llm_health_path)
        except ProviderError as exc:
            return ProviderHealth(name=self.provider_name, status=ProviderHealthStatus.UNAVAILABLE, message=str(exc))
        if isinstance(payload, dict) and payload.get("status") in {"ok", "healthy"}:
            return ProviderHealth(name=self.provider_name, status=ProviderHealthStatus.HEALTHY, message="provider responded healthy")
        return ProviderHealth(name=self.provider_name, status=ProviderHealthStatus.UNAVAILABLE, message="provider health response was malformed")

    def capabilities(self) -> ProviderCapabilities:
        runtime = self._runtime_config
        # Vision is supported by llama.cpp's multimodal chat transport when a
        # compatible model/mmproj is loaded. Audio/video are not advertised by
        # this adapter until a concrete transport contract exists for them.
        return ProviderCapabilities(
            chat=True, streaming=True, structured_output=True, tool_calling=True,
            vision=True, audio_input=False, video_input=False,
            context_window_tokens=runtime.context_window_tokens if runtime is not None else self.settings.context_window_tokens,
            max_output_tokens=runtime.max_output_tokens if runtime is not None else self.settings.llm_max_output_tokens,
        )

    def close(self) -> None:
        self.client.close()

    def _first_choice(self, payload: dict[str, object]) -> dict[str, object] | None:
        choices = payload.get("choices")
        return choices[0] if isinstance(choices, list) and choices and isinstance(choices[0], dict) else None

    def _extract_text(self, payload: dict[str, object]) -> str:
        choice = self._first_choice(payload)
        if choice:
            message = choice.get("message")
            if isinstance(message, dict):
                content = message.get("content")
                if isinstance(content, str):
                    return content
                if isinstance(content, list):
                    parts = [p.get("text", "") for p in content if isinstance(p, dict) and isinstance(p.get("text"), str)]
                    if parts:
                        return "".join(parts)
        if isinstance(payload.get("text"), str):
            return payload["text"]
        if isinstance(payload.get("content"), str):
            return payload["content"]
        if self._extract_tool_calls(payload):
            return ""
        raise ProviderError("provider returned a malformed chat response", provider_name=self.provider_name, operation="complete", retryable=False)

    def _extract_tool_calls(self, payload: dict[str, object]) -> list[LLMToolCall]:
        choice = self._first_choice(payload)
        if not choice or not isinstance(choice.get("message"), dict):
            return []
        raw_calls = choice["message"].get("tool_calls")
        if not isinstance(raw_calls, list):
            return []
        calls: list[LLMToolCall] = []
        for index, raw in enumerate(raw_calls):
            if not isinstance(raw, dict) or not isinstance(raw.get("function"), dict):
                continue
            function = raw["function"]
            name = function.get("name")
            if not isinstance(name, str) or not name.strip():
                continue
            arguments = function.get("arguments", {})
            if isinstance(arguments, str):
                try:
                    arguments = json.loads(arguments)
                except json.JSONDecodeError as exc:
                    raise ProviderError(f"tool '{name}' returned invalid JSON arguments: {exc}", provider_name=self.provider_name, operation="complete", retryable=False) from exc
            if not isinstance(arguments, dict):
                raise ProviderError(f"tool '{name}' returned non-object arguments", provider_name=self.provider_name, operation="complete", retryable=False)
            call_id = raw.get("id") if isinstance(raw.get("id"), str) and raw.get("id") else f"llm-call-{index + 1}"
            calls.append(LLMToolCall(id=call_id, name=name.strip(), arguments=arguments))
        return calls

    @staticmethod
    def _extract_timings(payload: dict[str, object]) -> dict[str, float | int]:
        raw = payload.get("timings")
        if not isinstance(raw, dict):
            return {}
        allowed = {"prompt_n", "prompt_ms", "prompt_per_token_ms", "prompt_per_second", "predicted_n", "predicted_ms", "predicted_per_token_ms", "predicted_per_second"}
        result: dict[str, float | int] = {}
        for key in allowed:
            value = raw.get(key)
            if isinstance(value, (int, float)) and value >= 0:
                result[key] = value
        return result

    def _extract_model_id(self, payload: dict[str, object]) -> str | None:
        model = payload.get("model")
        return model if isinstance(model, str) else (self._runtime_config.model_id if self._runtime_config is not None else self.settings.llm_model_id)

    def _extract_token_usage(self, payload: dict[str, object]) -> int | None:
        usage = payload.get("usage")
        return usage.get("total_tokens") if isinstance(usage, dict) and isinstance(usage.get("total_tokens"), int) else None

    def _extract_finish_reason(self, payload: dict[str, object]) -> str | None:
        choice = self._first_choice(payload)
        reason = choice.get("finish_reason") if choice else None
        return reason if isinstance(reason, str) else None
