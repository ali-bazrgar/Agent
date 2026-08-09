from superagent.llm.capabilities import ModelCapabilities, ModelCapabilityRegistry


def test_runtime_config_uses_model_provider_intersection() -> None:
    registry = ModelCapabilityRegistry()
    registry.register(
        ModelCapabilities(
            model_id="model",
            context_window_tokens=16384,
            max_output_tokens=4096,
            chat=True,
        )
    )
    provider = ModelCapabilities(
        model_id="provider",
        context_window_tokens=8192,
        max_output_tokens=2048,
        chat=True,
    )

    runtime = registry.runtime_config("model", provider=provider)

    assert runtime.model_id == "model"
    assert runtime.context_window_tokens == 8192
    assert runtime.max_output_tokens == 2048
    assert runtime.available_prompt_tokens == 6144


def test_runtime_config_never_reserves_more_output_than_context() -> None:
    registry = ModelCapabilityRegistry()
    registry.register(ModelCapabilities(model_id="model", context_window_tokens=4096, chat=True))
    provider = ModelCapabilities(model_id="provider", context_window_tokens=4096, chat=True)

    runtime = registry.runtime_config(
        "model",
        provider=provider,
        fallback_max_output_tokens=8192,
    )

    assert runtime.context_window_tokens == 4096
    assert runtime.max_output_tokens == 4096
    assert runtime.available_prompt_tokens == 0
