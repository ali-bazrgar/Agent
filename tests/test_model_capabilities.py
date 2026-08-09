import pytest

from superagent.llm.capabilities import EffectiveCapabilities, ModelCapabilities, ModelCapabilityRegistry


def test_effective_capabilities_are_provider_model_runtime_intersection() -> None:
    registry = ModelCapabilityRegistry()
    registry.register(
        ModelCapabilities(
            model_id="demo-model",
            context_window_tokens=131072,
            max_output_tokens=8192,
            chat=True,
            streaming=True,
            tool_calling=True,
            structured_output=True,
            vision=True,
            verified={"tool_calling", "chat", "streaming"},
        )
    )
    provider = ModelCapabilities(
        model_id="provider",
        context_window_tokens=32768,
        max_output_tokens=4096,
        chat=True,
        streaming=True,
        tool_calling=True,
        structured_output=False,
        vision=False,
    )

    effective = registry.effective("demo-model", provider=provider)

    assert isinstance(effective, EffectiveCapabilities)
    assert effective.context_window_tokens == 32768
    assert effective.max_output_tokens == 4096
    assert effective.tool_calling is True
    assert effective.structured_output is False
    assert effective.vision is False


def test_runtime_policy_can_disable_tools() -> None:
    registry = ModelCapabilityRegistry()
    registry.register(ModelCapabilities(model_id="model", tool_calling=True))
    provider = ModelCapabilities(model_id="provider", tool_calling=True)

    effective = registry.effective("model", provider=provider, tools_enabled=False)

    assert effective.tool_calling is False


def test_runtime_policy_can_disable_structured_output() -> None:
    registry = ModelCapabilityRegistry()
    registry.register(ModelCapabilities(model_id="model", structured_output=True))
    provider = ModelCapabilities(model_id="provider", structured_output=True)

    effective = registry.effective("model", provider=provider, structured_output_enabled=False)

    assert effective.structured_output is False


def test_unverified_capabilities_are_reported_and_can_be_blocked() -> None:
    registry = ModelCapabilityRegistry()
    registry.register(ModelCapabilities(model_id="model", chat=True, tool_calling=True))
    provider = ModelCapabilities(model_id="provider", chat=True, tool_calling=True)

    permissive = registry.effective("model", provider=provider)
    strict = registry.effective("model", provider=provider, require_verified=True)

    assert permissive.chat is True
    assert permissive.tool_calling is True
    assert "tool_calling" in permissive.unverified
    assert strict.chat is False
    assert strict.tool_calling is False


def test_verified_capability_survives_strict_resolution() -> None:
    registry = ModelCapabilityRegistry()
    registry.register(
        ModelCapabilities(model_id="model", chat=True, tool_calling=True, verified={"chat", "tool_calling"})
    )
    provider = ModelCapabilities(model_id="provider", chat=True, tool_calling=True)

    effective = registry.effective("model", provider=provider, require_verified=True)

    assert effective.chat is True
    assert effective.tool_calling is True
    assert effective.unverified == set()


def test_unknown_model_is_rejected() -> None:
    registry = ModelCapabilityRegistry()
    provider = ModelCapabilities(model_id="provider")

    with pytest.raises(KeyError):
        registry.effective("missing", provider=provider)
