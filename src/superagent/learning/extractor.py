from __future__ import annotations

import json
from uuid import uuid4
from datetime import datetime, timezone
from typing import Sequence

from superagent.models.domain import Flashcard, Source, KnowledgeItem, DocumentChunk
from superagent.providers.contracts import LLMProvider, LLMRequest


class FlashcardExtractor:
    """Service to extract learning items and generate flashcards from document chunks or source text."""

    def __init__(self, llm_provider: LLMProvider | None = None) -> None:
        self.llm_provider = llm_provider

    def extract_flashcards_from_chunk(
        self,
        chunk: DocumentChunk,
        source: Source | None = None,
        max_cards: int = 3,
    ) -> Sequence[Flashcard]:
        cards: list[Flashcard] = []
        
        # If LLM provider is available, use it to generate quality cards
        if self.llm_provider:
            try:
                prompt = (
                    f"Extract up to {max_cards} atomic flashcards (front question, back answer) "
                    f"from the following text snippet. Return JSON format as a list of objects with 'front' and 'back' keys.\n\n"
                    f"Text:\n{chunk.content}"
                )
                response = self.llm_provider.complete(LLMRequest(prompt=prompt, temperature=0.2))
                text = response.text.strip()
                if text.startswith("```json"):
                    text = text[7:]
                if text.endswith("```"):
                    text = text[:-3]
                parsed = json.loads(text.strip())
                if isinstance(parsed, list):
                    for item in parsed[:max_cards]:
                        front = item.get("front")
                        back = item.get("back")
                        if front and back:
                            card_id = f"fc-{uuid4().hex[:12]}"
                            cards.append(
                                Flashcard(
                                    flashcard_id=card_id,
                                    front=str(front),
                                    back=str(back),
                                    source=source or Source(source_id=chunk.document_id, source_type="document", uri=chunk.document_id),
                                    difficulty=0.4,
                                    created_at=datetime.now(timezone.utc),
                                    updated_at=datetime.now(timezone.utc),
                                )
                            )
            except Exception:
                pass  # Fallback to algorithmic extraction if LLM fails

        # Fallback / algorithmic heuristic if LLM produced nothing
        if not cards:
            sentences = [s.strip() for s in chunk.content.split(".") if len(s.strip()) > 15]
            for idx, sent in enumerate(sentences[:max_cards]):
                card_id = f"fc-{uuid4().hex[:12]}"
                cards.append(
                    Flashcard(
                        flashcard_id=card_id,
                        front=f"What is the key point regarding: {sent[:40]}...?",
                        back=sent,
                        source=source or Source(source_id=chunk.document_id, source_type="document", uri=chunk.document_id),
                        difficulty=0.3,
                        created_at=datetime.now(timezone.utc),
                        updated_at=datetime.now(timezone.utc),
                    )
                )

        return cards
