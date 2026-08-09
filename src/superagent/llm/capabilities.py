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


@dataclass
class ModelCapabilityRegistry:
    """In-process registry for explicit model capability declarations.

    The registry is deliberately provider-neutral. Providers may populate it from
    configuration, discovery endpoints, or a future persistent model catalog.
    """

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

    def list(self) -> list[ModelCapabilities]:
        return list(self._models.values())

    def clear(self) -> None:
        self._models.clear()
