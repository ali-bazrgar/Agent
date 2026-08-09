from __future__ import annotations

from datetime import datetime, timezone
import pytest

from superagent.application.container import AppContainer
from superagent.context import (
    ChatMessage,
    ContextBudget,
    ContextEngine,
    ContextItem,
    ContextItemKind,
    ContextRequest,
    PromptBuilder,
    TokenEstimator,
)
from superagent.core.errors import ValidationError
from superagent.models.domain import MemoryKind, MemoryRecord, MemoryStatus, Source
from superagent.retrieval.dense import SqliteDenseRetriever
from superagent.retrieval.models import RetrievalCandidate, RetrievalResult


def build_dummy_source(source_id: str = "src-1") -> Source:
    return Source(
        source_id=source_id,
        source_type="file",
        title="Test Source",
        content_hash="abc123hash",
    )


def test_cosine_similarity_clamping():
    v1 = [1.0, 0.0]
    v2 = [1.0, 0.0]
    score = SqliteDenseRetriever._cosine_similarity(v1, v2)
    assert score == 1.0
    v3 = [100.0, 0.0]
    v4 = [100.0, 0.0]
    score2 = SqliteDenseRetriever._cosine_similarity(v3, v4)
    assert -1.0 <= score2 <= 1.0


def test_token_estimator():
    estimator = TokenEstimator()
    assert estimator.estimate_text("") == 0
    assert estimator.estimate_text("abcd") == 1
    assert estimator.estimate_text("12345678") == 2
    msg = ChatMessage(role="user", content="Hello world!")
    assert estimator.estimate_message(msg) == estimator.estimate_text("Hello world!") + 4


def test_context_budget_invariant():
    budget = ContextBudget(total_context_window=1000, reserved_output_tokens=200)
    assert budget.available_prompt_tokens == 800
    with pytest.raises(ValidationError, match="Invalid context budget"):
        engine = ContextEngine()
        req = ContextRequest(
            query="Test query",
            budget=ContextBudget(total_context_window=500, reserved_output_tokens=500),
        )
        engine.build_context(req)


def test_user_query_preservation_and_system_messages():
    engine = ContextEngine()
    req = ContextRequest(
        query="What is the capital of France?",
        system_instructions=["You are a helpful assistant.", "Answer concisely."],
        budget=ContextBudget(total_context_window=1000, reserved_output_tokens=200),
    )
    result = engine.build_context(req)
    assert result.total_prompt_tokens <= result.total_context_window - result.reserved_output_tokens
    assert len(result.prompt_messages) >= 2
    assert result.prompt_messages[0].role == "system"
    assert "You are a helpful assistant." in result.prompt_messages[0].content
    assert "Answer concisely." in result.prompt_messages[0].content
    assert result.prompt_messages[-1].role == "user"
    assert result.prompt_messages[-1].content == "What is the capital of France?"


def test_empty_retrieval_and_empty_memory_results():
    engine = ContextEngine()
    req = ContextRequest(
        query="Explain relativity",
        retrieval_result=RetrievalResult(query="Explain relativity", candidates=[]),
        memories=[],
        budget=ContextBudget(total_context_window=1000, reserved_output_tokens=200),
    )
    result = engine.build_context(req)
    assert result.selection.dropped_items == []
    assert len(result.prompt_messages) == 1
    assert result.prompt_messages[0].content == "Explain relativity"


def test_knowledge_and_memory_ranking_and_selection():
    engine = ContextEngine()
    c1 = RetrievalCandidate(
        chunk_id="chk-1", document_id="doc-1", version_id="ver-1", source_id="src-1",
        content="Paris is the capital of France.", retrieval_method="dense", retrieval_score=0.95, reranker_score=0.98,
    )
    c2 = RetrievalCandidate(
        chunk_id="chk-2", document_id="doc-1", version_id="ver-1", source_id="src-1",
        content="France is in Western Europe.", retrieval_method="lexical", retrieval_score=0.70, reranker_score=0.75,
    )
    mem1 = MemoryRecord(
        memory_id="mem-1", kind=MemoryKind.USER, content="User lives in Europe.", confidence=0.9,
        importance=0.8, relevance=0.9, status=MemoryStatus.ACTIVE, source=build_dummy_source(),
    )
    req = ContextRequest(
        query="Tell me about Paris", system_instructions=["System base prompt"],
        retrieval_result=RetrievalResult(query="Tell me about Paris", candidates=[c1, c2]), memories=[mem1],
        budget=ContextBudget(total_context_window=2000, reserved_output_tokens=500),
    )
    result = engine.build_context(req)
    assert len(result.provenance) == 3
    assert any(p["chunk_id"] == "chk-1" for p in result.provenance)
    assert any(p["memory_id"] == "mem-1" for p in result.provenance)
    sys_msg = result.prompt_messages[0].content
    assert "Paris is the capital of France." in sys_msg
    assert "User lives in Europe." in sys_msg


def test_deduplication_of_knowledge_and_memories():
    engine = ContextEngine()
    c1 = RetrievalCandidate(
        chunk_id="chk-dup", document_id="doc-1", content="Duplicate knowledge content.", retrieval_method="dense", retrieval_score=0.90,
    )
    c2 = RetrievalCandidate(
        chunk_id="chk-dup", document_id="doc-1", content="Duplicate knowledge content.", retrieval_method="lexical", retrieval_score=0.80,
    )
    req = ContextRequest(
        query="Test query", retrieval_result=RetrievalResult(query="Test query", candidates=[c1, c2]),
        budget=ContextBudget(total_context_window=1000, reserved_output_tokens=200),
    )
    result = engine.build_context(req)
    k_items = [it for it in result.selection.selected_items if it.kind == ContextItemKind.KNOWLEDGE_CHUNK]
    assert len(k_items) == 1
    assert k_items[0].score == 0.90


def test_context_overflow_and_trimming():
    engine = ContextEngine()
    long_history = [
        ChatMessage(role="user" if i % 2 == 0 else "assistant", content=f"Message number {i} with some extra text.")
        for i in range(20)
    ]
    c1 = RetrievalCandidate(
        chunk_id="chk-long-1", document_id="doc-1",
        content="A very detailed knowledge chunk providing deep context about science " * 5,
        retrieval_score=0.85,
    )
    req = ContextRequest(
        query="What is science?", system_instructions=["Short system prompt"], conversation_history=long_history,
        retrieval_result=RetrievalResult(query="What is science?", candidates=[c1]),
        budget=ContextBudget(total_context_window=180, reserved_output_tokens=50),
    )
    result = engine.build_context(req)
    assert result.total_prompt_tokens + result.reserved_output_tokens <= result.total_context_window
    assert len(result.selection.dropped_items) > 0
    assert result.prompt_messages[-1].content == "What is science?"


def test_final_prompt_budget_trims_weakest_selected_item():
    engine = ContextEngine()
    request = ContextRequest(
        query="What should I remember?",
        system_instructions=["System instruction"],
        retrieval_candidates=[
            ContextItem(item_id="strong", kind=ContextItemKind.KNOWLEDGE_CHUNK, content="A" * 160, priority=40, score=0.95),
            ContextItem(item_id="weak", kind=ContextItemKind.KNOWLEDGE_CHUNK, content="B" * 160, priority=40, score=0.10),
        ],
        budget=ContextBudget(total_context_window=110, reserved_output_tokens=20),
    )
    result = engine.build_context(request)
    assert result.total_prompt_tokens + result.reserved_output_tokens <= result.total_context_window
    assert any(item.item_id == "weak" for item in result.selection.dropped_items)
    assert all(item.item_id != "weak" for item in result.selection.selected_items)


def test_deterministic_sorting_and_tie_breaking():
    item1 = ContextItem(item_id="b-item", kind=ContextItemKind.KNOWLEDGE_CHUNK, content="B", priority=40, score=0.8)
    item2 = ContextItem(item_id="a-item", kind=ContextItemKind.KNOWLEDGE_CHUNK, content="A", priority=40, score=0.8)
    item3 = ContextItem(item_id="c-item", kind=ContextItemKind.KNOWLEDGE_CHUNK, content="C", priority=40, score=0.9)
    from superagent.context.ranking import sort_context_items_deterministically
    sorted_res = sort_context_items_deterministically([item1, item2, item3])
    assert [x.item_id for x in sorted_res] == ["c-item", "a-item", "b-item"]


def test_extremely_small_budget_error_when_query_too_large():
    engine = ContextEngine()
    req = ContextRequest(
        query="This is an extremely long query that exceeds the available prompt budget entirely." * 10,
        budget=ContextBudget(total_context_window=30, reserved_output_tokens=20),
    )
    with pytest.raises(ValidationError, match="User query token count"):
        engine.build_context(req)


def test_app_container_context_engine_wireup():
    container = AppContainer()
    engine = container.context_engine
    assert isinstance(engine, ContextEngine)
