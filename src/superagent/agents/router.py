from __future__ import annotations

import re

from superagent.agents.models import AgentRequest, AgentRoute
from superagent.agents.ports import AgentRouterPort


class AgentRouter(AgentRouterPort):
    """Deterministic router for identifying necessary execution capabilities."""

    def route_request(self, request: AgentRequest) -> AgentRoute:
        message = request.message.strip().lower()

        # Check explicit execution config overrides first
        if "force_route" in request.execution_config:
            forced = request.execution_config["force_route"]
            if isinstance(forced, AgentRoute):
                return forced
            try:
                return AgentRoute(forced)
            except ValueError:
                pass

        has_history = len(request.conversation_history) > 0

        # Keywords indicating retrieval / research
        retrieval_keywords = [
            "search",
            "retrieve",
            "document",
            "knowledge",
            "find in",
            "paper",
            "source",
            "according to",
            "what is",
            "explain",
            "how does",
            "summarize document",
        ]

        # Keywords referring to past memory/conversation
        memory_keywords = [
            "remember",
            "my name",
            "earlier",
            "i told you",
            "my preference",
            "last time",
            "we discussed",
            "what did i say",
        ]

        # Keywords indicating tool / math execution
        tool_keywords = [
            "calculate",
            "compute",
            "math",
            "calculator",
            "what time is it",
            "current time",
            "time in",
        ]

        # Keywords indicating web research
        research_keywords = [
            "search web",
            "web search",
            "research web",
            "latest news",
            "today's news",
            "current events",
            "recent research",
        ]

        # Check math expressions e.g. "1847 * 392"
        is_math_expr = bool(re.search(r"\b\d+\s*[\+\-\*\/\%]\s*\d+\b", message)) or any(
            kw in message for kw in tool_keywords
        )
        needs_research = any(kw in message for kw in research_keywords)

        if is_math_expr:
            return AgentRoute.TOOL
        elif needs_research:
            return AgentRoute.RESEARCH

        needs_retrieval = any(re.search(r"\b" + re.escape(kw) + r"\b", message) for kw in retrieval_keywords)
        needs_memory = any(re.search(r"\b" + re.escape(kw) + r"\b", message) for kw in memory_keywords) or has_history

        if needs_retrieval and needs_memory:
            return AgentRoute.RETRIEVAL_AND_MEMORY
        elif needs_retrieval:
            return AgentRoute.RETRIEVAL
        elif needs_memory:
            return AgentRoute.MEMORY
        else:
            return AgentRoute.DIRECT
