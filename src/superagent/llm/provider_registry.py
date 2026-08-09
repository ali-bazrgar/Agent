from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any

from superagent.providers.contracts import LLMProvider


ProviderFactory = Callable[..., LLMProvider]


@dataclass
class LLMProviderRegistry:
    """Maps provider identifiers to factories without coupling Agent to implementations."""

    _factories: dict[str, ProviderFactory] = field(default_factory=dict)

    def register(self, provider_id: str, factory: ProviderFactory) -> None:
        normalized = provider_id.strip().lower()
        if not normalized:
            raise ValueError("provider_id must not be empty")
        if normalized in self._factories:
            raise ValueError(f"Provider already registered: {provider_id}")
        self._factories[normalized] = factory

    def replace(self, provider_id: str, factory: ProviderFactory) -> None:
        normalized = provider_id.strip().lower()
        if not normalized:
            raise ValueError("provider_id must not be empty")
        self._factories[normalized] = factory

    def unregister(self, provider_id: str) -> None:
        self._factories.pop(provider_id.strip().lower(), None)

    def get(self, provider_id: str) -> ProviderFactory | None:
        return self._factories.get(provider_id.strip().lower())

    def require(self, provider_id: str) -> ProviderFactory:
        factory = self.get(provider_id)
        if factory is None:
            available = ", ".join(sorted(self._factories)) or "<none>"
            raise KeyError(f"Unknown LLM provider '{provider_id}'. Available: {available}")
        return factory

    def create(self, provider_id: str, **kwargs: Any) -> LLMProvider:
        provider = self.require(provider_id)(**kwargs)
        if not isinstance(provider, LLMProvider):
            raise TypeError(f"Provider factory '{provider_id}' returned an invalid provider")
        return provider

    def list(self) -> list[str]:
        return sorted(self._factories)


DEFAULT_PROVIDER_REGISTRY = LLMProviderRegistry()
