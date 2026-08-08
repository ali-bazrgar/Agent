from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any

from pydantic import BaseModel, Field

from superagent.tools.executor import ToolExecutor
from superagent.tools.models import ToolCall, ToolExecutionContext, ToolExecutionStatus
from superagent.tools.ports import ToolExecutorPort

logger = logging.getLogger(__name__)


class ResearchEvidence(BaseModel):
    """Ephemeral research evidence from web search and fetch operations."""

    evidence_id: str = Field(min_length=1)
    source_url: str = Field(min_length=1)
    title: str = Field(default="")
    snippet: str = Field(default="")
    content: str = Field(default="")
    retrieved_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    metadata: dict[str, Any] = Field(default_factory=dict)


class ResearchPipeline:
    """Orchestrates web search and webpage fetching into structured ephemeral research evidence."""

    def __init__(
        self,
        executor: ToolExecutorPort,
        max_search_results: int = 3,
        max_pages_to_fetch: int = 2,
    ) -> None:
        self.executor = executor
        self.max_search_results = max_search_results
        self.max_pages_to_fetch = max_pages_to_fetch

    def conduct_research(
        self,
        query: str,
        context: ToolExecutionContext | None = None,
    ) -> list[ResearchEvidence]:
        evidence_list: list[ResearchEvidence] = []
        context = context or ToolExecutionContext()

        # Step 1: Execute web search tool call
        search_call = ToolCall(
            tool_call_id=f"call-search-{int(datetime.now(timezone.utc).timestamp())}",
            tool_name="web_search",
            arguments={"query": query, "max_results": self.max_search_results},
        )

        search_res = self.executor.execute_tool(search_call, context)
        if search_res.status != ToolExecutionStatus.SUCCESS or not isinstance(search_res.output, dict):
            logger.warning(f"Research pipeline search step failed: {search_res.error}")
            return evidence_list

        raw_results = search_res.output.get("results", [])
        if not raw_results:
            return evidence_list

        urls_to_fetch: list[dict[str, Any]] = []

        # Step 2: Select relevant search results
        for idx, item in enumerate(raw_results[: self.max_search_results]):
            url = item.get("url")
            title = item.get("title", "Untitled")
            snippet = item.get("snippet", "")

            # Create base search snippet evidence
            if url:
                evidence = ResearchEvidence(
                    evidence_id=f"evid-search-{idx+1}",
                    source_url=url,
                    title=title,
                    snippet=snippet,
                    content=snippet,
                    metadata={"stage": "search_snippet"},
                )
                evidence_list.append(evidence)

                if len(urls_to_fetch) < self.max_pages_to_fetch:
                    urls_to_fetch.append(item)

        # Step 3: Fetch top pages for full content extraction
        for idx, item in enumerate(urls_to_fetch):
            url = item.get("url")
            if not url:
                continue

            fetch_call = ToolCall(
                tool_call_id=f"call-fetch-{idx+1}",
                tool_name="web_fetch",
                arguments={"url": url},
            )

            fetch_res = self.executor.execute_tool(fetch_call, context)
            if fetch_res.status == ToolExecutionStatus.SUCCESS and isinstance(fetch_res.output, dict):
                full_text = fetch_res.output.get("text", "")
                page_title = fetch_res.output.get("title") or item.get("title") or "Untitled"

                if full_text:
                    evidence_list.append(
                        ResearchEvidence(
                            evidence_id=f"evid-fetch-{idx+1}",
                            source_url=url,
                            title=page_title,
                            snippet=item.get("snippet", ""),
                            content=full_text,
                            metadata={"stage": "page_content", "content_length": len(full_text)},
                        )
                    )

        return evidence_list
