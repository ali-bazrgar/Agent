from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field

from superagent.llm.capabilities import CapabilitySet, EffectiveCapabilities, ModelCapabilities


class ModelCapabilityOverride(BaseModel):
    """Optional operator-declared metadata for a concrete model.

    Overrides may fill in or tighten model metadata, but can never enable a
    capability that the provider does not expose. Boolean fields are optional
    so omitted values leave discovered metadata unchanged.
    """

    chat: bool | None = None
    streaming: bool | None = None
    embeddings: bool | None = None
    batch_embeddings: bool | None = None
    reranking: bool | None = None
    structured_output: bool | None = None
    tool_calling: bool | None = None
    vision: bool | None = None
    audio_input: bool | None = None
    video_input: bool | None = None
    reasoning: bool | None = None
    context_window_tokens: int | None = Field(default=None, ge=1)
    max_output_tokens: int | None = Field(default=None, ge=1)


_BOOLEAN_FIELDS = (
    "chat", "streaming", "embeddings", "batch_embeddings", "reranking",
    "structured_output", "tool_calling", "vision", "audio_input", "video_input",
    "reasoning",
)


def apply_override(model: ModelCapabilities, override: ModelCapabilityOverride) -> ModelCapabilities:
    """Apply explicit metadata without inventing unspecified values."""
    data = model.model_dump()
    for name in _BOOLEAN_FIELDS:
        value = getattr(override, name)
        if value is not None:
            data[name] = value
    if override.context_window_tokens is not None:
        data["context_window_tokens"] = override.context_window_tokens
    if override.max_output_tokens is not None:
        data["max_output_tokens"] = override.max_output_tokens
    return ModelCapabilities.model_validate(data)


def constrain_to_provider(
    model: ModelCapabilities,
    provider: CapabilitySet,
) -> EffectiveCapabilities:
    """Prevent overrides/discovery from claiming unsupported provider features."""
    values: dict[str, Any] = {}
    for name in _BOOLEAN_FIELDS:
        values[name] = bool(getattr(model, name)) and bool(getattr(provider, name))
    contexts = [v for v in (model.context_window_tokens, provider.context_window_tokens) if v is not None]
    outputs = [v for v in (model.max_output_tokens, provider.max_output_tokens) if v is not None]
    return EffectiveCapabilities(
        model_id=model.model_id,
        context_window_tokens=min(contexts) if contexts else None,
        max_output_tokens=min(outputs) if outputs else None,
        **values,
    )
