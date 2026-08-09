from __future__ import annotations

import re
from typing import Any, Sequence

from superagent.agents.models import VerificationResult, VerificationStatus
from superagent.agents.ports import AgentVerifierPort


_STOPWORDS = {
    "the", "and", "that", "this", "with", "from", "have", "has", "for", "are", "was", "were",
    "into", "about", "what", "which", "when", "where", "who", "how", "why", "does", "than", "then",
    "they", "their", "there", "will", "would", "could", "should", "can", "not", "but", "also",
}


class AgentVerifier(AgentVerifierPort):
    """Conservative deterministic verifier using claim/evidence lexical alignment.

    Provenance without evidence text is never treated as proof. This avoids the
    previous false-positive behaviour where every claim was marked supported merely
    because a chunk id existed.
    """

    @staticmethod
    def _sentences(text: str) -> list[str]:
        return [part.strip() for part in re.split(r"(?<=[.!?])\s+|\n+", text) if len(part.strip()) > 10]

    @staticmethod
    def _terms(text: str) -> set[str]:
        return {word for word in re.findall(r"[\w-]{4,}", text.lower()) if word not in _STOPWORDS}

    def verify(self, query: str, candidate_answer: str, context_provenance: Sequence[dict[str, Any]]) -> VerificationResult:
        if not candidate_answer or not candidate_answer.strip():
            return VerificationResult(verified=False, status=VerificationStatus.UNKNOWN, confidence=0.0, unsupported_claims=["Empty candidate answer"])

        if not context_provenance:
            return VerificationResult(
                verified=False,
                status=VerificationStatus.UNKNOWN,
                confidence=0.0,
                unsupported_claims=self._sentences(candidate_answer) or [candidate_answer.strip()],
                evidence=[],
            )

        evidence_records: list[dict[str, Any]] = []
        for item in context_provenance:
            evidence_text = item.get("content") or item.get("text") or item.get("snippet")
            if not isinstance(evidence_text, str) or not evidence_text.strip():
                nested = item.get("provenance")
                if isinstance(nested, dict):
                    evidence_text = nested.get("content") or nested.get("text") or nested.get("snippet")
            if isinstance(evidence_text, str) and evidence_text.strip():
                evidence_records.append({"text": evidence_text, "item_id": item.get("item_id"), "chunk_id": item.get("chunk_id"), "score": item.get("score")})

        claims = self._sentences(candidate_answer)
        supported: list[str] = []
        unsupported: list[str] = []
        evidence: list[dict[str, Any]] = []

        for claim in claims:
            claim_terms = self._terms(claim)
            best_match: tuple[float, dict[str, Any] | None] = (0.0, None)
            for record in evidence_records:
                evidence_terms = self._terms(record["text"])
                if not claim_terms or not evidence_terms:
                    continue
                overlap = len(claim_terms & evidence_terms) / len(claim_terms)
                if overlap > best_match[0]:
                    best_match = (overlap, record)
            score, record = best_match
            if score >= 0.55:
                supported.append(claim)
                if record is not None:
                    evidence.append({"claim": claim, "match_score": round(score, 3), "item_id": record.get("item_id"), "chunk_id": record.get("chunk_id"), "score": record.get("score")})
            else:
                unsupported.append(claim)

        if not claims:
            return VerificationResult(verified=False, status=VerificationStatus.UNKNOWN, confidence=0.0, unsupported_claims=[candidate_answer.strip()], evidence=[])

        verified = bool(supported) and not unsupported
        status = VerificationStatus.SUPPORTED if verified else VerificationStatus.UNSUPPORTED
        confidence = (len(supported) / len(claims)) * 0.85 if claims else 0.0
        return VerificationResult(
            verified=verified,
            status=status,
            confidence=round(confidence, 3),
            supported_claims=supported,
            unsupported_claims=unsupported,
            contradictory_claims=[],
            evidence=evidence,
        )
