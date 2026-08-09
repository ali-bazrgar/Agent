from superagent.retrieval import RetrievalIntent, RetrievalPlanner, RetrievalSource


def test_plans_conversation_queries() -> None:
    plan = RetrievalPlanner().plan("دیروز درباره RAG چی گفتیم؟", token_budget=900)
    assert plan.intent is RetrievalIntent.CONVERSATION
    assert plan.sources == (RetrievalSource.CONVERSATION,)
    assert plan.token_budget == 900


def test_plans_memory_queries() -> None:
    plan = RetrievalPlanner().plan("ترجیحات من درباره مدل‌ها چی بود؟")
    assert plan.intent is RetrievalIntent.MEMORY
    assert plan.sources == (RetrievalSource.MEMORY,)


def test_plans_document_queries() -> None:
    plan = RetrievalPlanner().plan("در PDF مربوط به RAG چه چیزی آمده؟")
    assert plan.intent is RetrievalIntent.MIXED
    assert plan.sources == (RetrievalSource.DOCUMENT, RetrievalSource.KNOWLEDGE)
    assert plan.rerank is not None and plan.rerank.enabled is True


def test_defaults_to_knowledge() -> None:
    plan = RetrievalPlanner().plan("روش hybrid retrieval را توضیح بده")
    assert plan.intent is RetrievalIntent.KNOWLEDGE
    assert plan.sources == (RetrievalSource.KNOWLEDGE,)


def test_rejects_invalid_budget() -> None:
    try:
        RetrievalPlanner().plan("RAG", token_budget=0)
    except ValueError as exc:
        assert "token_budget" in str(exc)
    else:
        raise AssertionError("expected ValueError")
