from __future__ import annotations

import pytest

from superagent.llm.provider_registry import LLMProviderRegistry
from superagent.providers.contracts import LLMProvider, ProviderCapabilities, ProviderHealth, ProviderHealthStatus


class FakeProvider(LLMProvider):
    def complete(self, request):
        raise NotImplementedError

    def check_health(self):
        return ProviderHealth(name="fake", status=ProviderHealthStatus.HEALTHY)

    def capabilities(self):
        return ProviderCapabilities(chat=True)


def test_registry_normalizes_ids_and_creates_provider() -> None:
    registry = LLMProviderRegistry()
    registry.register("  My-Provider ", FakeProvider)

    assert registry.list() == ["my-provider"]
    assert isinstance(registry.create("MY-PROVIDER"), FakeProvider)


def test_registry_rejects_duplicate_and_unknown_provider() -> None:
    registry = LLMProviderRegistry()
    registry.register("fake", FakeProvider)

    with pytest.raises(ValueError):
        registry.register("FAKE", FakeProvider)
    with pytest.raises(KeyError):
        registry.require("missing")


def test_registry_rejects_invalid_factory_result() -> None:
    registry = LLMProviderRegistry()
    registry.register("broken", lambda: object())

    with pytest.raises(TypeError):
        registry.create("broken")
