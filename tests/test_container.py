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
