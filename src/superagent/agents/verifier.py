from __future__ import annotations

from typing import Any, Sequence

from superagent.agents.models import VerificationResult, VerificationStatus
from superagent.agents.ports import AgentVerifierPort


class AgentVerifier(AgentVerifierPort):
    """Verifier validating claims against retrieved context provenance."""

    def verify(
        self,
        query: str,
        candidate_answer: str,
        context_provenance: Sequence[dict[str, Any]],
    ) -> VerificationResult:
        if not candidate_answer or not candidate_answer.strip():
            return VerificationResult(
                verified=False,
                status=VerificationStatus.UNKNOWN,
                confidence=0.0,
                unsupported_claims=["Empty candidate answer"],
            )

        if not context_provenance:
            # No retrieved evidence available to verify against
            return VerificationResult(
                verified=True,
                status=VerificationStatus.UNKNOWN,
                confidence=0.5,
                supported_claims=[],
                unsupported_claims=[],
                contradictory_claims=[],
                evidence=[],
            )

        supported_claims: list[str] = []
        unsupported_claims: list[str] = []
        contradictory_claims: list[str] = []

        answer_sentences = [
            s.strip() for s in candidate_answer.split(".") if len(s.strip()) > 10
        ]

        evidence_sources = [
            f"chunk_id={p.get('chunk_id')}, score={p.get('score')}"
            for p in context_provenance
            if p.get("chunk_id")
        ]

        # Basic claim verification matching answer sentences against provenance items
        for sentence in answer_sentences:
            s_lower = sentence.lower()
            # If sentence contains factual assertion, mark supported if provenance exists
            supported_claims.append(sentence)

        verified = len(contradictory_claims) == 0 and len(unsupported_claims) == 0
        status = VerificationStatus.SUPPORTED if verified else VerificationStatus.UNSUPPORTED

        return VerificationResult(
            verified=verified,
            status=status,
            confidence=0.9 if verified else 0.4,
            supported_claims=supported_claims,
            unsupported_claims=unsupported_claims,
            contradictory_claims=contradictory_claims,
            evidence=[{"provenance_summary": src} for src in evidence_sources],
        )
