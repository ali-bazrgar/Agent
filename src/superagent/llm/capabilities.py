from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from pydantic import BaseModel, Field


class CapabilitySet(BaseModel):
    """Canonical capability contract shared by providers and concrete models."""

    chat: bool = False
    streaming: bool = False
    embeddings: bool = False
    batch_embeddings: bool = False
    reranking: bool = False
    structured_output: bool = False
    tool_calling: bool = False
    vision: bool = False
    audio_input: bool = False
    video_input: bool = False
    context_window_tokens: int | None = Field(default=None, ge=1)
    max_output_tokens: int | None = Field(default=None, ge=1)


class ModelCapabilities(CapabilitySet):
    """Capabilities declared for one concrete model, plus verification evidence."""

    model_id: str = Field(min_length=1)
    reasoning: bool = False
    metadata: dict[str, Any] = Field(default_factory=dict)
    verified: set[str] = Field(default_factory=set)

    def is_verified(self, capability: str) -> bool:
        return capability in self.verified


class EffectiveCapabilities(CapabilitySet):
    """Capabilities actually usable after policy and verification checks."""

    model_id: str
    reasoning: bool = False
    unverified: set[str] = Field(default_factory=set)


@dataclass
class ModelCapabilityRegistry:
    """Provider-neutral registry for explicit concrete-model capability declarations."""

    _models: dict[str, ModelCapabilities] = field(default_factory=dict)

    def register(self, capabilities: ModelCapabilities) -> None:
        self._models[capabilities.model_id] = capabilities

    def get(self, model_id: str) -> ModelCapabilities | None:
        return self._models.get(model_id)

    def require(self, model_id: str) -> ModelCapabilities:
        capabilities = self.get(model_id)
        if capabilities is None:
            raise KeyError(f"No capability metadata registered for model: {model_id}")
        return capabilities

    def supports(self, model_id: str, capability: str) -> bool:
        model = self.get(model_id)
        if model is None:
            return False
        value = getattr(model, capability, None)
        return bool(value) if isinstance(value, bool) else value is not None

    def effective(
        self,
        model_id: str,
        *,
        provider: CapabilitySet,
        tools_enabled: bool = True,
        structured_output_enabled: bool = True,
        require_verified: bool = False,
    ) -> EffectiveCapabilities:
        """Intersect model/provider declarations and optionally require evidence."""
        model = self.require(model_id)
        boolean_fields = (
            "chat", "streaming", "embeddings", "batch_embeddings", "reranking",
            "structured_output", "tool_calling", "vision", "audio_input", "video_input",
            "reasoning",
        )
        values: dict[str, Any] = {}
        unverified: set[str] = set()
        for name in boolean_fields:
            declared = bool(getattr(model, name)) and bool(getattr(provider, name))
            if declared and not model.is_verified(name):
                unverified.add(name)
            values[name] = declared and (not require_verified or model.is_verified(name))
        values["tool_calling"] = values["tool_calling"] and tools_enabled
        values["structured_output"] = values["structured_output"] and structured_output_enabled
        contexts = [v for v in (model.context_window_tokens, provider.context_window_tokens) if v is not None]
        outputs = [v for v in (model.max_output_tokens, provider.max_output_tokens) if v is not None]
        return EffectiveCapabilities(
            model_id=model_id,
            context_window_tokens=min(contexts) if contexts else None,
            max_output_tokens=min(outputs) if outputs else None,
            unverified=unverified,
            **values,
        )

    def runtime_config(
        self,
        model_id: str,
        *,
        provider: CapabilitySet,
        temperature: float = 0.7,
        top_p: float = 1.0,
        timeout_seconds: float = 60.0,
        tools_enabled: bool = True,
        structured_output_enabled: bool = True,
        require_verified: bool = False,
        fallback_context_window_tokens: int = 8192,
        fallback_max_output_tokens: int | None = None,
    ):
        """Resolve effective capabilities without inventing a generation cap."""
        from superagent.llm.runtime import ModelRuntimeConfig

        effective = self.effective(
            model_id,
            provider=provider,
            tools_enabled=tools_enabled,
            structured_output_enabled=structured_output_enabled,
            require_verified=require_verified,
        )
        return ModelRuntimeConfig.from_effective_capabilities(
            effective,
            temperature=temperature,
            top_p=top_p,
            timeout_seconds=timeout_seconds,
            fallback_context_window_tokens=fallback_context_window_tokens,
            fallback_max_output_tokens=fallback_max_output_tokens,
        )

    def list(self) -> list[ModelCapabilities]:
        return list(self._models.values())

    def clear(self) -> None:
        self._models.clear()
