from __future__ import annotations

import pytest

from superagent.config.settings import Settings
from superagent.llm.runtime import ModelRuntimeConfig


def test_runtime_config_reserves_output_from_context_window() -> None:
    config = ModelRuntimeConfig(context_window_tokens=8192, max_output_tokens=2048)
    assert config.available_prompt_tokens == 6144


def test_runtime_config_rejects_prompt_that_exceeds_context() -> None:
    config = ModelRuntimeConfig(context_window_tokens=4096, max_output_tokens=1024)
    with pytest.raises(ValueError, match="exceeds model context window"):
        config.validate_prompt_budget(prompt_tokens=3073)


def test_settings_produce_one_runtime_configuration() -> None:
    settings = Settings(
        llm_model_id="test-model",
        context_window_tokens=16384,
        llm_max_output_tokens=2048,
        llm_temperature=0.4,
        llm_top_p=0.9,
        provider_total_timeout_seconds=45,
    )
    runtime = settings.model_runtime_config()
    assert runtime.model_id == "test-model"
    assert runtime.context_window_tokens == 16384
    assert runtime.max_output_tokens == 2048
    assert runtime.temperature == 0.4
    assert runtime.top_p == 0.9
    assert runtime.timeout_seconds == 45
