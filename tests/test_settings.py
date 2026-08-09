from __future__ import annotations

from superagent.config.settings import Settings


def test_settings_read_environment_overrides() -> None:
    settings = Settings(
        _env_file=None,
        environment="testing",
        debug=True,
        app_port=9001,
        context_window_tokens=16384,
    )

    assert settings.environment == "testing"
    assert settings.debug is True
    assert settings.app_port == 9001
    assert settings.context_window_tokens == 16384
    assert settings.llm_max_output_tokens is None


def test_explicit_generation_cap_is_preserved() -> None:
    settings = Settings(_env_file=None, llm_max_output_tokens=4096)
    assert settings.llm_max_output_tokens == 4096
