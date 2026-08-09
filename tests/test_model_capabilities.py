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


def test_unknown_model_is_rejected() -> None:
    registry = ModelCapabilityRegistry()
    provider = ModelCapabilities(model_id="provider")

    with pytest.raises(KeyError):
        registry.effective("missing", provider=provider)
