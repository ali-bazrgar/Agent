from __future__ import annotations

import pytest

from superagent.models.domain import Document, MemoryRecord, Source


def test_document_title_must_not_be_blank() -> None:
    with pytest.raises(ValueError):
        Document(document_id="doc-1", title="   ", source=Source(source_id="src-1", source_type="file"))


def test_memory_record_confidence_is_bounded() -> None:
    with pytest.raises(ValueError):
        MemoryRecord(
            memory_id="mem-1",
            kind="working",
            content="hello",
            confidence=1.5,
            importance=0.1,
            relevance=0.2,
            source=Source(source_id="src-1", source_type="conversation"),
        )
