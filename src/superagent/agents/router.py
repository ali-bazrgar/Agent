from __future__ import annotations

import re

from superagent.agents.models import AgentRequest, AgentRoute
from superagent.agents.ports import AgentRouterPort


class AgentRouter(AgentRouterPort):
    """Route only explicit overrides by default; semantic capability choice belongs to the LLM."""

    def route_request(self, request: AgentRequest) -> AgentRoute:
        forced = request.execution_config.get("force_route")
        if forced is not None:
            if isinstance(forced, AgentRoute):
                return forced
            try:
                return AgentRoute(str(forced))
            except ValueError:
                pass

        # In the normal agentic path, the model receives the complete tool surface
        # and decides whether memory, knowledge retrieval, web research, math, time,
        # or no tool is appropriate. This deliberately avoids language-specific
        # keyword triggers, including explicit Persian storage phrases.
        if bool(request.execution_config.get("llm_driven_tools", True)):
            return AgentRoute.DIRECT

        return self._legacy_route(request)

    @staticmethod
    def _legacy_route(request: AgentRequest) -> AgentRoute:
        """Compatibility route for deterministic/non-agentic execution mode."""
        message = request.message.strip().lower()
        has_history = bool(request.conversation_history)

        retrieval_keywords = ["search", "retrieve", "document", "knowledge", "find in", "paper", "source", "according to", "what is", "explain", "how does", "summarize document"]
        memory_keywords = ["remember", "my name", "earlier", "i told you", "my preference", "last time", "we discussed", "what did i say"]
        tool_keywords = ["calculate", "compute", "math", "calculator", "what time is it", "current time", "time in"]
        research_keywords = ["search web", "web search", "research web", "latest news", "today's news", "current events", "recent research"]

        is_math_expr = bool(re.search(r"\b\d+\s*[\+\-\*\/\%]\s*\d+\b", message)) or any(kw in message for kw in tool_keywords)
        if is_math_expr:
            return AgentRoute.TOOL
        if any(kw in message for kw in research_keywords):
            return AgentRoute.RESEARCH

        needs_retrieval = any(re.search(r"\b" + re.escape(kw) + r"\b", message) for kw in retrieval_keywords)
        needs_memory = any(re.search(r"\b" + re.escape(kw) + r"\b", message) for kw in memory_keywords) or has_history
        if needs_retrieval and needs_memory:
            return AgentRoute.RETRIEVAL_AND_MEMORY
        if needs_retrieval:
            return AgentRoute.RETRIEVAL
        if needs_memory:
            return AgentRoute.MEMORY
        return AgentRoute.DIRECT
