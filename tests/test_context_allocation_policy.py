from superagent.context import ChatMessage, ContextBudget, ContextEngine, ContextRequest
from superagent.context.models import ContextItem, ContextItemKind
from superagent.models.domain import MemoryKind, MemoryRecord, MemoryStatus, Source


def _memory(memory_id: str, content: str) -> MemoryRecord:
    return MemoryRecord(
        memory_id=memory_id,
        kind=MemoryKind.USER,
        content=content,
        confidence=1.0,
        importance=1.0,
        relevance=1.0,
        status=MemoryStatus.ACTIVE,
        source=Source(source_id="test", source_type="test", title="test", content_hash="hash"),
    )


def test_context_allocation_can_disable_memory_and_history() -> None:
    result = ContextEngine().build_context(
        ContextRequest(
            query="current question",
            conversation_history=[ChatMessage(role="user", content="old conversation")],
            memories=[_memory("m1", "durable user fact")],
            metadata={
                "_context_allocation": {
                    "use_conversation_history": False,
                    "use_memory": False,
                    "use_knowledge": True,
                }
            },
            budget=ContextBudget(total_context_window=1000, reserved_output_tokens=100),
        )
    )
    kinds = {item.kind for item in result.selection.selected_items}
    assert ContextItemKind.CONVERSATION_MESSAGE not in kinds
    assert ContextItemKind.MEMORY not in kinds


def test_context_allocation_enforces_memory_and_knowledge_token_budgets() -> None:
    knowledge = [
        ContextItem(item_id="k1", kind=ContextItemKind.KNOWLEDGE_CHUNK, content="a" * 40, priority=40, score=0.9),
        ContextItem(item_id="k2", kind=ContextItemKind.KNOWLEDGE_CHUNK, content="b" * 40, priority=40, score=0.8),
    ]
    result = ContextEngine().build_context(
        ContextRequest(
            query="question",
            retrieval_candidates=knowledge,
            memories=[_memory("m1", "memory one"), _memory("m2", "memory two")],
            metadata={
                "_context_allocation": {
                    "max_knowledge_tokens": 10,
                    "max_memory_tokens": 4,
                    "min_retrieval_score": 0.85,
                }
            },
            budget=ContextBudget(total_context_window=1000, reserved_output_tokens=100),
        )
    )
    selected_knowledge = [i for i in result.selection.selected_items if i.kind == ContextItemKind.KNOWLEDGE_CHUNK]
    selected_memory = [i for i in result.selection.selected_items if i.kind == ContextItemKind.MEMORY]
    assert sum(i.estimated_tokens for i in selected_knowledge) <= 10
    assert sum(i.estimated_tokens for i in selected_memory) <= 4
    assert all(i.score >= 0.85 for i in selected_knowledge)
