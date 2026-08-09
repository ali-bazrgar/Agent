def test_context_models_import_without_retrieval_package_cycle() -> None:
    from superagent.context.models import ChatMessage, ContextBuildResult

    assert ChatMessage is not None
    assert ContextBuildResult is not None
