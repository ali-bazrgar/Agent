from __future__ import annotations

from typing import Any

from superagent.retrieval import HybridRetriever, RetrievalQuery
from superagent.tools.models import RiskLevel, ToolCall, ToolDefinition, ToolExecutionContext, ToolExecutionStatus, ToolResult
from superagent.tools.ports import ToolProvider


class KnowledgeSearchTool(ToolProvider):
    """Expose the existing hybrid knowledge pipeline as a model-selected tool."""

    def __init__(self, retriever: HybridRetriever) -> None:
        self.retriever = retriever

    @property
    def definition(self) -> ToolDefinition:
        return ToolDefinition(
            name="knowledge.search",
            description=(
                "Search the user's indexed knowledge base when the answer needs information from stored documents. "
                "Decide semantically whether retrieval is necessary; do not rely on trigger phrases."
            ),
            input_schema={
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "Natural-language search query for the indexed knowledge base."},
                    "limit": {"type": "integer", "minimum": 1, "maximum": 10, "default": 5},
                },
                "required": ["query"],
                "additionalProperties": False,
            },
            output_schema={"type": "object", "properties": {"results": {"type": "array"}}},
            requires_network=False,
            risk_level=RiskLevel.LOW,
            timeout_seconds=30.0,
        )

    def execute(self, call: ToolCall, context: ToolExecutionContext | None = None) -> ToolResult:
        query = call.arguments.get("query")
        if not isinstance(query, str) or not query.strip():
            return ToolResult(tool_call_id=call.tool_call_id, tool_name=call.tool_name, status=ToolExecutionStatus.INVALID_ARGUMENTS, error="query must be a non-empty string")
        try:
            limit = min(10, max(1, int(call.arguments.get("limit", 5))))
            result = self.retriever.retrieve(
                RetrievalQuery(
                    text=query.strip(),
                    top_k=limit,
                    candidate_k=max(limit * 2, 10),
                )
            )
            results: list[dict[str, Any]] = []
            for candidate in result.candidates:
                results.append(
                    {
                        "content": candidate.content,
                        "chunk_id": candidate.chunk_id,
                        "document_id": candidate.document_id,
                        "version_id": candidate.version_id,
                        "score": candidate.reranker_score if candidate.reranker_score is not None else candidate.retrieval_score,
                        "retrieval_method": candidate.retrieval_method,
                        "provenance": candidate.provenance,
                    }
                )
            return ToolResult(
                tool_call_id=call.tool_call_id,
                tool_name=call.tool_name,
                status=ToolExecutionStatus.SUCCESS,
                output={"results": results, "count": len(results), "query": query.strip()},
                metadata={"retrieval_used": bool(results)},
            )
        except Exception as exc:
            return ToolResult(tool_call_id=call.tool_call_id, tool_name=call.tool_name, status=ToolExecutionStatus.ERROR, error=f"knowledge search failed: {exc}")
