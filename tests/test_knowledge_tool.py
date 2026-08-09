from __future__ import annotations

from superagent.retrieval.models import RetrievalCandidate, RetrievalResult
from superagent.tools.knowledge import KnowledgeSearchTool
from superagent.tools.models import ToolCall, ToolExecutionContext, ToolExecutionStatus


class FakeRetriever:
    def retrieve(self, query):
        return RetrievalResult(
            query=query.text,
            candidates=[
                RetrievalCandidate(
                    chunk_id="chunk-1",
                    document_id="doc-1",
                    content="Architecture uses a bounded model-selected tool loop.",
                    retrieval_score=0.91,
                    retrieval_method="hybrid",
                    provenance={"document": "architecture.md"},
                )
            ],
            total_candidates=1,
            dense_count=1,
            lexical_count=1,
            fused_count=1,
            reranked=False,
            token_budget=None,
            estimated_tokens=10,
            duration_ms=1.0,
        )


def test_knowledge_search_tool_returns_provenance_and_results():
    tool = KnowledgeSearchTool(FakeRetriever())
    result = tool.execute(
        ToolCall(tool_call_id="call-1", tool_name="knowledge.search", arguments={"query": "how does routing work"}),
        ToolExecutionContext(execution_id="exec-1"),
    )

    assert result.status == ToolExecutionStatus.SUCCESS
    assert result.output["count"] == 1
    assert result.output["results"][0]["chunk_id"] == "chunk-1"
    assert result.output["results"][0]["provenance"]["document"] == "architecture.md"
