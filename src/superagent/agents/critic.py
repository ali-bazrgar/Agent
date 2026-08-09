from __future__ import annotations

import logging
from typing import Any

from superagent.agents.models import CritiqueResult
from superagent.agents.ports import AgentCriticPort
from superagent.providers.contracts import LLMProvider, LLMRequest

logger = logging.getLogger(__name__)


class AgentCritic(AgentCriticPort):
    """Critic evaluating generated response quality and factuality."""

    def __init__(self, llm_provider: LLMProvider | None = None) -> None:
        self.llm_provider = llm_provider

    def critique(self, query: str, context_str: str, response_text: str) -> CritiqueResult:
        if not response_text or not response_text.strip():
            return CritiqueResult(
                passed=False,
                score=0.0,
                factuality_score=0.0,
                relevance_score=0.0,
                completeness_score=0.0,
                issues=["Response text is empty."],
                required_revision="Generate a non-empty answer addressing the user query.",
                reasoning="Empty response generated.",
            )

        issues: list[str] = []
        if "Internal Server Error" in response_text or "HTTP 500" in response_text:
            issues.append("Response contains server error text.")

        if context_str and len(context_str) > 50:
            query_words = [w for w in query.lower().split() if len(w) > 3]
            overlap_in_context = any(w in context_str.lower() for w in query_words)
            if overlap_in_context and ("i don't know" in response_text.lower() or "no information" in response_text.lower()):
                issues.append("Response claims no information despite context containing relevant facts.")

        if self.llm_provider is not None:
            try:
                eval_prompt = (
                    f"Evaluate the following AI response for query: '{query}'\n\n"
                    f"Context provided:\n{context_str[:1000]}\n\n"
                    f"AI Response:\n{response_text[:1000]}\n\n"
                    "Reply ONLY in format: PASSED or FAILED | Score: 0.0-1.0 | Issues: <issues>"
                )
                req = LLMRequest(prompt=eval_prompt, max_tokens=100, temperature=0.0, metadata={"disable_tools": True})
                llm_res = self.llm_provider.complete(req)
                res_text = llm_res.text.strip()
                if "FAILED" in res_text:
                    issues.append("LLM critic flagged response quality or factual issues.")
            except Exception as exc:
                logger.warning(f"Critic LLM evaluation failed gracefully: {exc}")

        passed = len(issues) == 0
        score = 1.0 if passed else 0.5
        return CritiqueResult(
            passed=passed,
            score=score,
            factuality_score=score,
            relevance_score=score,
            completeness_score=score,
            issues=issues,
            required_revision="Address flagged issues and refine accuracy against context." if not passed else None,
            reasoning="Critique evaluated response." if passed else f"Critique identified issues: {'; '.join(issues)}",
        )
