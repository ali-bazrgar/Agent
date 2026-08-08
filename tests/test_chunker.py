from __future__ import annotations

import pytest

from superagent.knowledge.ingest.chunker import TextChunker


def test_chunker_argument_validation() -> None:
    with pytest.raises(ValueError):
        TextChunker(chunk_size=0)

    with pytest.raises(ValueError):
        TextChunker(chunk_size=100, chunk_overlap=-5)

    with pytest.raises(ValueError):
        TextChunker(chunk_size=100, chunk_overlap=100)


def test_chunker_empty_and_short_input() -> None:
    chunker = TextChunker(chunk_size=100, chunk_overlap=20)

    assert chunker.chunk_text("") == []
    assert chunker.chunk_text("   \n\r\n   ") == []

    short = "Hello world."
    chunks = chunker.chunk_text(short)
    assert len(chunks) == 1
    assert chunks[0].chunk_index == 0
    assert chunks[0].content == "Hello world."
    assert chunks[0].character_count == len("Hello world.")
    assert chunks[0].token_count == 2


def test_chunker_normalization_and_splitting() -> None:
    chunker = TextChunker(chunk_size=50, chunk_overlap=10)

    text = "First paragraph here.\r\nSecond paragraph here with more text.\r\nThird paragraph."
    chunks = chunker.chunk_text(text)

    assert len(chunks) > 1
    # Check stable indices
    for idx, c in enumerate(chunks):
        assert c.chunk_index == idx
        assert c.content != ""
        assert c.token_count > 0


def test_chunker_preserves_base_metadata() -> None:
    chunker = TextChunker(chunk_size=50, chunk_overlap=10)
    meta = {"doc_id": "123"}

    chunks = chunker.chunk_text("This is some sample text for testing metadata propagation.", base_metadata=meta)
    assert len(chunks) > 0
    for c in chunks:
        assert c.metadata["doc_id"] == "123"
        assert "start_char" in c.metadata
        assert "end_char" in c.metadata
