from __future__ import annotations

import logging
import urllib.parse
import urllib.request
import json
from typing import Any

from superagent.providers.contracts import WebResearchProvider, WebResearchRequest, WebResearchResponse
from superagent.tools.models import (
    RiskLevel,
    ToolCall,
    ToolDefinition,
    ToolExecutionContext,
    ToolExecutionStatus,
    ToolResult,
)
from superagent.tools.ports import ToolProvider

logger = logging.getLogger(__name__)


class DefaultWebSearchProvider(WebResearchProvider):
    """Default WebResearchProvider implementing lightweight web search."""

    def __init__(self, api_key: str | None = None, search_url: str | None = None) -> None:
        self.api_key = api_key
        self.search_url = search_url

    def search(self, request: WebResearchRequest) -> WebResearchResponse:
        query = request.query.strip()
        if not query:
            return WebResearchResponse(results=[], provider_name="default_search")

        # If custom search URL or API key is provided, attempt HTTP search
        if self.search_url:
            try:
                params = urllib.parse.urlencode({"q": query, "limit": request.max_results})
                url = f"{self.search_url}?{params}"
                req = urllib.request.Request(url, headers={"User-Agent": "SuperAgent/1.0"})
                with urllib.request.urlopen(req, timeout=5.0) as resp:
                    if resp.status == 200:
                        data = json.loads(resp.read().decode("utf-8"))
                        raw_results = data.get("results", [])
                        normalized = []
                        for item in raw_results[: request.max_results]:
                            normalized.append({
                                "title": item.get("title", "Untitled"),
                                "url": item.get("url", ""),
                                "snippet": item.get("snippet", item.get("description", "")),
                                "source": item.get("source", "web"),
                                "published_at": item.get("published_at"),
                            })
                        return WebResearchResponse(results=normalized, provider_name="custom_search_api")
            except Exception as exc:
                logger.warning(f"External search provider failed gracefully: {exc}")

        # Provider unavailable / unconfigured fallback
        return WebResearchResponse(
            results=[],
            provider_name="unconfigured_search_provider",
        )


class WebSearchTool(ToolProvider):
    """Tool wrapping WebResearchProvider for agent search capabilities."""

    def __init__(self, provider: WebResearchProvider | None = None) -> None:
        self.provider = provider or DefaultWebSearchProvider()

    @property
    def definition(self) -> ToolDefinition:
        return ToolDefinition(
            name="web_search",
            description="Searches the web for up-to-date information, news, and references.",
            input_schema={
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Search query keywords.",
                    },
                    "max_results": {
                        "type": "integer",
                        "description": "Maximum number of search results to return (1-10).",
                        "default": 5,
                    },
                },
                "required": ["query"],
            },
            output_schema={
                "type": "object",
                "properties": {
                    "query": {"type": "string"},
                    "results": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "title": {"type": "string"},
                                "url": {"type": "string"},
                                "snippet": {"type": "string"},
                                "source": {"type": "string"},
                                "published_at": {"type": "string"},
                            },
                        },
                    },
                },
            },
            requires_network=True,
            risk_level=RiskLevel.MEDIUM,
            timeout_seconds=10.0,
            enabled=True,
        )

    def execute(
        self,
        call: ToolCall,
        context: ToolExecutionContext | None = None,
    ) -> ToolResult:
        query = call.arguments.get("query")
        if not query or not isinstance(query, str) or not query.strip():
            return ToolResult(
                tool_call_id=call.tool_call_id,
                tool_name="web_search",
                status=ToolExecutionStatus.INVALID_ARGUMENTS,
                error="Argument 'query' must be a non-empty string.",
            )

        max_results = call.arguments.get("max_results", 5)
        if not isinstance(max_results, int) or max_results < 1:
            max_results = 5
        max_results = min(max_results, 10)

        req = WebResearchRequest(query=query.strip(), max_results=max_results)

        try:
            res = self.provider.search(req)
            return ToolResult(
                tool_call_id=call.tool_call_id,
                tool_name="web_search",
                status=ToolExecutionStatus.SUCCESS,
                output={
                    "query": query.strip(),
                    "results": res.results,
                    "provider": res.provider_name or "web_search",
                },
            )
        except Exception as exc:
            logger.warning(f"WebSearchTool execution failed: {exc}")
            return ToolResult(
                tool_call_id=call.tool_call_id,
                tool_name="web_search",
                status=ToolExecutionStatus.ERROR,
                error=f"Web search failed: {exc}",
            )
