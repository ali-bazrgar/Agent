from __future__ import annotations

import re
from typing import Sequence

from superagent.memory.models import MemoryCandidate, MemoryPolicy
from superagent.memory.ports import MemoryExtractorPort
from superagent.models.domain import MemoryKind


class MemoryExtractor(MemoryExtractorPort):
    """Deterministic extractor for explicit and high-confidence memory candidates.

    The extractor is intentionally conservative: explicit memory instructions are
    handled before generic heuristics, and Persian/English variants are supported.
    """

    _EXPLICIT_MEMORY_PATTERNS = (
        r"(?:این اطلاعات(?:\s+رو|\s+را)?|این(?:\s+مورد)?)\s*(?:ذخیره|ثبت|یادداشت|به خاطر)\s*(?:کن|کنید|کنش|کنه)?",
        r"(?:این را|این رو|این مورد را|این مورد رو)\s*(?:ذخیره|ثبت|یادداشت)\s*(?:کن|کنید)?",
        r"(?:ذخیره|ثبت|یادداشت)\s*(?:کن|کنید)?",
        r"(?:remember|save|store|keep)\s+(?:this|that|the following)?",
    )

    _PERSIAN_USER_PATTERNS = (
        (r"(?:من|اسم من)\s+(?:هستم|است)", MemoryKind.USER, 0.85, 0.85),
        (r"اسمم\s+", MemoryKind.USER, 0.9, 0.9),
        (r"من\s+.*(?:دوست دارم|ترجیح می.?دهم|ترجیح میدم)", MemoryKind.USER, 0.85, 0.85),
        (r"من\s+.*(?:کار می.?کنم|زندگی می.?کنم)", MemoryKind.USER, 0.8, 0.8),
        (r"(?:یادم|یاد)\s+باش(?:د|ه)", MemoryKind.PROCEDURAL, 0.85, 0.85),
        (r"همیشه\s+", MemoryKind.PROCEDURAL, 0.75, 0.75),
    )

    _ENGLISH_USER_PATTERNS = (
        (r"\bmy name is\b", MemoryKind.USER, 0.9, 0.9),
        (r"\bi am a\b", MemoryKind.USER, 0.8, 0.8),
        (r"\bi work at\b", MemoryKind.USER, 0.8, 0.8),
        (r"\bi live in\b", MemoryKind.USER, 0.8, 0.8),
        (r"\bi prefer\b", MemoryKind.USER, 0.85, 0.85),
        (r"\bi like\b", MemoryKind.USER, 0.7, 0.7),
        (r"\bremember that\b", MemoryKind.SEMANTIC, 0.9, 0.9),
        (r"\balways\b", MemoryKind.PROCEDURAL, 0.75, 0.75),
    )

    def __init__(self, policy: MemoryPolicy | None = None) -> None:
        self.policy = policy or MemoryPolicy()

    def extract_candidates(
        self,
        user_message: str,
        assistant_message: str,
        execution_id: str | None = None,
    ) -> list[MemoryCandidate]:
        user_clean = user_message.strip()
        if not user_clean or len(user_clean) < 5:
            return []

        lowered = user_clean.casefold()
        noise_words = {
            "hello", "hi", "hey", "thanks", "thank you", "ok", "okay", "bye", "goodbye",
            "سلام", "درود", "ممنون", "مرسی", "باشه", "خداحافظ",
        }
        if lowered in noise_words:
            return []

        explicit = self._extract_explicit_memory(user_clean, execution_id)
        if explicit:
            return explicit

        patterns = (*self._PERSIAN_USER_PATTERNS, *self._ENGLISH_USER_PATTERNS)
        for pattern, kind, importance, confidence in patterns:
            if re.search(pattern, lowered, flags=re.IGNORECASE):
                candidate = self._candidate(
                    user_clean,
                    kind,
                    importance,
                    confidence,
                    execution_id,
                    extractor="heuristic_pattern",
                    pattern=pattern,
                )
                return [candidate] if self._passes_policy(candidate) else []

        if not self._looks_like_question(user_clean) and len(user_clean) > 15:
            candidate = self._candidate(
                user_clean,
                MemoryKind.EPISODIC,
                0.5,
                0.6,
                execution_id,
                extractor="episodic_user_statement",
            )
            return [candidate] if self._passes_policy(candidate) else []

        return []

    def _extract_explicit_memory(
        self,
        message: str,
        execution_id: str | None,
    ) -> list[MemoryCandidate]:
        content = message
        matched_pattern: str | None = None
        for pattern in self._EXPLICIT_MEMORY_PATTERNS:
            match = re.search(pattern, content, flags=re.IGNORECASE)
            if match:
                matched_pattern = pattern
                content = (content[: match.start()] + " " + content[match.end() :]).strip(" :،,\t\n")
                break

        if matched_pattern is None:
            return []

        # A bare "save this" is not enough to manufacture a memory.
        if len(content) < 5 or self._looks_like_question(content):
            return []

        candidate = self._candidate(
            content,
            self._classify_explicit_content(content),
            0.9,
            0.95,
            execution_id,
            extractor="explicit_memory_instruction",
            pattern=matched_pattern,
        )
        return [candidate] if self._passes_policy(candidate) else []

    @staticmethod
    def _classify_explicit_content(content: str) -> MemoryKind:
        lowered = content.casefold()
        if re.search(r"(?:من|my|i)\b.*(?:دوست دارم|ترجیح|like|prefer|name is|اسم)", lowered):
            return MemoryKind.USER
        if re.search(r"(?:همیشه|always|یادت|remember)", lowered):
            return MemoryKind.PROCEDURAL
        return MemoryKind.SEMANTIC

    @staticmethod
    def _looks_like_question(content: str) -> bool:
        lowered = content.casefold().strip()
        return "?" in content or lowered.startswith(("چرا ", "چطور ", "چگونه ", "کجا ", "چه زمانی ", "what ", "why ", "how ", "where "))

    @staticmethod
    def _candidate(
        content: str,
        kind: MemoryKind,
        importance: float,
        confidence: float,
        execution_id: str | None,
        *,
        extractor: str,
        pattern: str | None = None,
    ) -> MemoryCandidate:
        metadata = {"extractor": extractor}
        if pattern:
            metadata["pattern"] = pattern
        return MemoryCandidate(
            content=content,
            kind=kind,
            importance=importance,
            confidence=confidence,
            relevance=0.8,
            source_execution_id=execution_id,
            metadata=metadata,
        )

    def _passes_policy(self, candidate: MemoryCandidate) -> bool:
        return (
            candidate.confidence >= self.policy.min_confidence
            and candidate.importance >= self.policy.min_importance
            and candidate.kind in self.policy.allowed_kinds
        )
