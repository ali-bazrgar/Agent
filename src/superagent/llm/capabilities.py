from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from pydantic import BaseModel, Field


class ModelCapabilities(BaseModel):
    """Capabilities and limits of one concrete model, independent of provider."""

    model_id: str = Field(min_length=1)
    context_window_tokens: int | None = Field(default=None, ge=1)
    max_output_tokens: int | None = Field(default=None, ge=1)
    chat: bool = True
    streaming: bool = False
    tool_calling: bool = False
    structured_output: bool = False
    vision: bool = False
    audio_input: bool = False
    video_input: bool = False
    reasoning: bool = False
    embeddings: bool = False
    metadata: dict[str, Any] = Field(default_factory=dict)


class EffectiveCapabilities(BaseModel):
    """Capabilities actually usable after provider/model/runtime policy intersection."""

    model_id: str
    context_window_tokens: int | None = None
    max_output_tokens: int | None = None
    chat: bool = False
    streaming: bool = False
    tool_calling: bool = False
    structured_output: bool = False
    vision: bool = False
    audio_input: bool = False
    video_input: bool = False
    reasoning: bool = False
    embeddings: bool = False


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
        provider: ModelCapabilities,
        tools_enabled: bool = True,
        structured_output_enabled: bool = True,
    ) -> EffectiveCapabilities:
        """Return the intersection of model metadata, provider support and runtime policy."""
        model = self.require(model_id)
        boolean_fields = (
            "chat", "streaming", "tool_calling", "structured_output", "vision",
            "audio_input", "video_input", "reasoning", "embeddings",
        )
        values: dict[str, Any] = {name: bool(getattr(model, name)) and bool(getattr(provider, name)) for name in boolean_fields}
        values["tool_calling"] = values["tool_calling"] and tools_enabled
        values["structured_output"] = values["structured_output"] and structured_output_enabled
        contexts = [v for v in (model.context_window_tokens, provider.context_window_tokens) if v is not None]
        outputs = [v for v in (model.max_output_tokens, provider.max_output_tokens) if v is not None]
        return EffectiveCapabilities(
            model_id=model_id,
            context_window_tokens=min(contexts) if contexts else None,
            max_output_tokens=min(outputs) if outputs else None,
            **values,
        )

    def list(self) -> list[ModelCapabilities]:
        return list(self._models.values())

    def clear(self) -> None:
        self._models.clear()
