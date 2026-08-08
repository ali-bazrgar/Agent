from __future__ import annotations

import re
from typing import Sequence

from superagent.memory.models import MemoryCandidate, MemoryPolicy
from superagent.memory.ports import MemoryExtractorPort
from superagent.models.domain import MemoryKind


class MemoryExtractor(MemoryExtractorPort):
    """Deterministic extractor for conversation memory candidates."""

    def __init__(self, policy: MemoryPolicy | None = None) -> None:
        self.policy = policy or MemoryPolicy()

    def extract_candidates(
        self,
        user_message: str,
        assistant_message: str,
        execution_id: str | None = None,
    ) -> list[MemoryCandidate]:
        candidates: list[MemoryCandidate] = []
        user_clean = user_message.strip()

        if not user_clean or len(user_clean) < 5:
            return candidates

        # Skip trivial greetings or acknowledgement noise
        lowered = user_clean.lower()
        noise_words = {"hello", "hi", "hey", "thanks", "thank you", "ok", "okay", "bye", "goodbye"}
        if lowered in noise_words:
            return candidates

        # Rule 1: User personal preferences or assertions ("I like", "My name is", "I work at", "I prefer")
        user_patterns = [
            (r"\bmy name is\b", MemoryKind.USER, 0.9, 0.9),
            (r"\bi am a\b", MemoryKind.USER, 0.8, 0.8),
            (r"\bi work at\b", MemoryKind.USER, 0.8, 0.8),
            (r"\bi live in\b", MemoryKind.USER, 0.8, 0.8),
            (r"\bi prefer\b", MemoryKind.USER, 0.85, 0.85),
            (r"\bi like\b", MemoryKind.USER, 0.7, 0.7),
            (r"\bremember that\b", MemoryKind.SEMANTIC, 0.9, 0.9),
            (r"\balways\b", MemoryKind.PROCEDURAL, 0.75, 0.75),
        ]

        matched = False
        for pattern, kind, importance, confidence in user_patterns:
            if re.search(pattern, lowered):
                cand = MemoryCandidate(
                    content=user_clean,
                    kind=kind,
                    importance=importance,
                    confidence=confidence,
                    relevance=0.8,
                    source_execution_id=execution_id,
                    metadata={"extractor": "heuristic_pattern", "pattern": pattern},
                )
                if self._passes_policy(cand):
                    candidates.append(cand)
                matched = True
                break

        # Rule 2: Generic factual or informative user query if not a simple noise
        if not matched and len(user_clean) > 15 and "?" not in user_clean:
            cand = MemoryCandidate(
                content=user_clean,
                kind=MemoryKind.EPISODIC,
                importance=0.5,
                confidence=0.6,
                relevance=0.6,
                source_execution_id=execution_id,
                metadata={"extractor": "episodic_user_statement"},
            )
            if self._passes_policy(cand):
                candidates.append(cand)

        return candidates

    def _passes_policy(self, candidate: MemoryCandidate) -> bool:
        if candidate.confidence < self.policy.min_confidence:
            return False
        if candidate.importance < self.policy.min_importance:
            return False
        if candidate.kind not in self.policy.allowed_kinds:
            return False
        return True
