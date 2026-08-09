from superagent.llm.capabilities import ModelCapabilities, ModelCapabilityRegistry
from superagent.llm.capability_policy import CapabilityPolicy
from superagent.providers.contracts import ProviderCapabilities


def test_provider_capabilities_do_not_invent_multimodal_support():
    provider = ProviderCapabilities(chat=True, streaming=True, tool_calling=True)
    assert provider.vision is False
    assert provider.audio_input is False
    assert provider.video_input is False


def test_runtime_capability_resolution_has_no_hidden_output_cap():
    registry = ModelCapabilityRegistry()
    registry.register(ModelCapabilities(model_id="local", chat=True, streaming=True, context_window_tokens=8192, verified={"chat", "streaming"}))
    effective = CapabilityPolicy(registry).effective("local", ProviderCapabilities(chat=True, streaming=True, context_window_tokens=8192))
    runtime = registry.runtime_config("local", provider=ProviderCapabilities(chat=True, streaming=True, context_window_tokens=8192))
    assert effective.context_window_tokens == 8192
    assert effective.max_output_tokens is None
    assert runtime.max_output_tokens is None
