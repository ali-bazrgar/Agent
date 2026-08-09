from superagent.context.models import ContextItem, ContextItemKind
from superagent.context.ranking import deduplicate_context_items


def test_deduplication_keeps_highest_score_for_same_chunk() -> None:
    weaker = ContextItem(
        item_id="weak",
        kind=ContextItemKind.KNOWLEDGE_CHUNK,
        content="same content",
        chunk_id="chunk-1",
        priority=40,
        score=0.30,
    )
    stronger = weaker.model_copy(update={"item_id": "strong", "score": 0.90})

    result = deduplicate_context_items([weaker, stronger])

    assert len(result) == 1
    assert result[0].item_id == "strong"


def test_deduplication_keeps_better_priority_before_score() -> None:
    low_priority = ContextItem(
        item_id="low",
        kind=ContextItemKind.MEMORY,
        content="same memory",
        memory_id="memory-1",
        priority=70,
        score=0.99,
    )
    high_priority = low_priority.model_copy(update={"item_id": "high", "priority": 50, "score": 0.20})

    result = deduplicate_context_items([low_priority, high_priority])

    assert len(result) == 1
    assert result[0].item_id == "high"
