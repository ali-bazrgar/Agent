from __future__ import annotations

from superagent.application.container import AppContainer


def test_container_wires_repositories(temporary_settings) -> None:
    container = AppContainer(settings=temporary_settings)

    assert container.document_repository is not None
    assert container.chunk_repository is not None
    assert container.memory_repository is not None
    assert container.execution_repository is not None
    assert container.flashcard_repository is not None
    assert container.review_repository is not None


def test_container_resolves_and_injects_llm_runtime_config(temporary_settings) -> None:
    temporary_settings.llm_model_id = "container-model"
    temporary_settings.context_window_tokens = 16384
    temporary_settings.llm_max_output_tokens = 2048
    temporary_settings.llm_temperature = 0.3
    temporary_settings.llm_top_p = 0.85

    container = AppContainer(settings=temporary_settings)

    assert container.runtime_config is not None
    assert container.runtime_config.model_id == "container-model"
    assert container.runtime_config.context_window_tokens == 16384
    assert container.runtime_config.max_output_tokens == 2048
    assert container.runtime_config.temperature == 0.3
    assert container.runtime_config.top_p == 0.85
    provider_runtime = getattr(container.llm_provider, "runtime_config", None)
    assert provider_runtime == container.runtime_config
