from __future__ import annotations

from typing import Any

from superagent.llm.capabilities import EffectiveCapabilities, ModelCapabilities, ModelCapabilityRegistry
from superagent.providers.contracts import ProviderCapabilities


class CapabilityPolicy:
    """Resolve the capabilities that are actually usable at runtime."""

    def __init__(
        self,
        registry: ModelCapabilityRegistry,
        *,
        require_verified: bool = False,
        tools_enabled: bool = True,
        structured_output_enabled: bool = True,
    ) -> None:
        self.registry = registry
        self.require_verified = require_verified
        self.tools_enabled = tools_enabled
        self.structured_output_enabled = structured_output_enabled

    def register_model(
        self,
        model_id: str,
        provider: ProviderCapabilities,
        *,
        overrides: dict[str, Any] | None = None,
    ) -> ModelCapabilities:
        overrides = overrides or {}
        boolean_fields = (
            "chat", "streaming", "embeddings", "batch_embeddings", "reranking",
            "structured_output", "tool_calling", "vision", "audio_input", "video_input",
            "reasoning",
        )
        values = {name: bool(overrides.get(name, getattr(provider, name, False))) for name in boolean_fields}
        values["context_window_tokens"] = overrides.get("context_window_tokens", provider.context_window_tokens)
        values["max_output_tokens"] = overrides.get("max_output_tokens", provider.max_output_tokens)
        values["verified"] = set(overrides.get("verified", []))
        values["metadata"] = dict(overrides.get("metadata", {}))
        capabilities = ModelCapabilities(model_id=model_id, **values)
        self.registry.register(capabilities)
        return capabilities

    def effective(self, model_id: str, provider: ProviderCapabilities) -> EffectiveCapabilities:
        return self.registry.effective(
            model_id,
            provider=provider,
            tools_enabled=self.tools_enabled,
            structured_output_enabled=self.structured_output_enabled,
            require_verified=self.require_verified,
        )
