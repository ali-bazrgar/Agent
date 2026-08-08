from __future__ import annotations

from superagent.application.container import AppContainer
from superagent.models.domain import Document, DocumentChunk, ExecutionState, Flashcard, MemoryRecord, Review, Source


def test_database_initialization_and_repository_round_trips(temporary_settings) -> None:
    container = AppContainer(settings=temporary_settings)

    doc = Document(
        document_id="doc-1",
        title="Phase 1 notes",
        source=Source(source_id="src-1", source_type="file", uri="file:///tmp/doc.txt"),
        metadata={"category": "notes"},
    )
    saved_doc = container.document_repository.create_document(doc)
    assert saved_doc.document_id == "doc-1"
    assert container.document_repository.get_document("doc-1").title == "Phase 1 notes"

    chunk = DocumentChunk(
        chunk_id="chunk-1",
        document_id="doc-1",
        content="The foundation is ready",
        chunk_index=0,
        token_count=6,
    )
    container.chunk_repository.create_chunk(chunk)
    chunks = container.chunk_repository.list_chunks_for_document("doc-1")
    assert len(chunks) == 1

    memory = MemoryRecord(
        memory_id="mem-1",
        kind="working",
        content="Important note",
        confidence=0.9,
        importance=0.8,
        relevance=0.7,
        source=Source(source_id="src-1", source_type="conversation"),
    )
    container.memory_repository.create_memory(memory)
    assert container.memory_repository.get_memory("mem-1").content == "Important note"

    flashcard = Flashcard(
        flashcard_id="card-1",
        front="What is Phase 1?",
        back="A foundational scaffold",
        source=Source(source_id="src-1", source_type="document"),
    )
    container.flashcard_repository.create_flashcard(flashcard)
    assert container.flashcard_repository.get_flashcard("card-1").front == "What is Phase 1?"

    review = Review(review_id="review-1", flashcard_id="card-1", outcome="correct", interval_days=1, ease_factor=2.5)
    container.review_repository.create_review(review)
    assert container.review_repository.list_reviews_for_flashcard("card-1")[0].outcome == "correct"

    execution = ExecutionState(execution_id="exec-1", request_id="req-1", status="initialized")
    container.execution_repository.create_execution(execution)
    assert container.execution_repository.get_execution("exec-1").status == "initialized"
