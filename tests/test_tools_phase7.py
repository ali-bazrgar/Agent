from __future__ import annotations

import unittest
from unittest.mock import MagicMock, patch

from superagent.agents.models import AgentExecutionStatus, AgentRequest, AgentRoute
from superagent.agents.planner import AgentPlanner
from superagent.agents.router import AgentRouter
from superagent.context.models import ContextItemKind
from superagent.providers.contracts import WebResearchProvider, WebResearchRequest, WebResearchResponse
from superagent.tools.calculator import CalculatorTool
from superagent.tools.executor import ToolExecutor
from superagent.tools.models import (
    RiskLevel,
    ToolCall,
    ToolDefinition,
    ToolExecutionContext,
    ToolExecutionStatus,
    ToolResult,
)
from superagent.tools.ports import ToolProvider
from superagent.tools.registry import ToolRegistry
from superagent.tools.research import ResearchPipeline
from superagent.tools.time_tool import TimeTool
from superagent.tools.web_fetch import WebFetchProvider, WebFetchTool
from superagent.tools.web_search import DefaultWebSearchProvider, WebSearchTool


class DummyTool(ToolProvider):
    def __init__(self, name: str = "dummy", enabled: bool = True):
        self._name = name
        self._enabled = enabled

    @property
    def definition(self) -> ToolDefinition:
        return ToolDefinition(
            name=self._name,
            description="Dummy tool for testing",
            enabled=self._enabled,
        )

    def execute(self, call: ToolCall, context: ToolExecutionContext | None = None) -> ToolResult:
        return ToolResult(
            tool_call_id=call.tool_call_id,
            tool_name=self._name,
            status=ToolExecutionStatus.SUCCESS,
            output={"echo": call.arguments},
        )


class TestPhase7ToolSystem(unittest.TestCase):

    def test_tool_registry(self):
        registry = ToolRegistry()
        tool1 = DummyTool("calculator")
        tool2 = DummyTool("web_search")

        registry.register(tool1)
        registry.register(tool2)

        self.assertTrue(registry.has("calculator"))
        self.assertTrue(registry.has("web_search"))
        self.assertFalse(registry.has("unknown_tool"))
        self.assertEqual(len(registry.list_tools()), 2)

        tool1_updated = DummyTool("calculator")
        registry.register(tool1_updated)
        self.assertEqual(len(registry.list_tools()), 2)

        registry.unregister("calculator")
        self.assertFalse(registry.has("calculator"))

    def test_calculator_tool(self):
        calc = CalculatorTool()

        call1 = ToolCall(tool_call_id="c1", tool_name="calculator", arguments={"expression": "1847 * 392"})
        res1 = calc.execute(call1)
        self.assertEqual(res1.status, ToolExecutionStatus.SUCCESS)
        self.assertEqual(res1.output["result"], 724024)

        call2 = ToolCall(tool_call_id="c2", tool_name="calculator", arguments={"expression": "(2 + 3) * 4"})
        res2 = calc.execute(call2)
        self.assertEqual(res2.output["result"], 20)

        call3 = ToolCall(tool_call_id="c3", tool_name="calculator", arguments={"expression": "10 / 0"})
        res3 = calc.execute(call3)
        self.assertEqual(res3.status, ToolExecutionStatus.ERROR)
        self.assertIn("Division by zero", res3.error)

        call_malicious = ToolCall(
            tool_call_id="c4",
            tool_name="calculator",
            arguments={"expression": "__import__('os').system('ls')"},
        )
        res_malicious = calc.execute(call_malicious)
        self.assertIn(res_malicious.status, [ToolExecutionStatus.SECURITY_REJECTED, ToolExecutionStatus.ERROR])

    def test_time_tool(self):
        time_tool = TimeTool()

        call1 = ToolCall(tool_call_id="t1", tool_name="current_time", arguments={"timezone": "America/New_York"})
        res1 = time_tool.execute(call1)
        self.assertEqual(res1.status, ToolExecutionStatus.SUCCESS)
        self.assertIn("datetime", res1.output)
        self.assertEqual(res1.output["timezone"], "America/New_York")

        call2 = ToolCall(tool_call_id="t2", tool_name="current_time", arguments={"timezone": "Invalid/Timezone"})
        res2 = time_tool.execute(call2)
        self.assertEqual(res2.status, ToolExecutionStatus.ERROR)
        self.assertIn("Invalid or unknown timezone", res2.error)

    def test_tool_executor_secrets_scrubbing(self):
        registry = ToolRegistry()

        class SecretLeakingTool(ToolProvider):
            @property
            def definition(self) -> ToolDefinition:
                return ToolDefinition(name="leak_secret", description="Leaking tool")

            def execute(self, call: ToolCall, context: ToolExecutionContext | None = None) -> ToolResult:
                return ToolResult(
                    tool_call_id=call.tool_call_id,
                    tool_name="leak_secret",
                    status=ToolExecutionStatus.SUCCESS,
                    output={"key": "api_key: sk-123456789012345678901234"},
                    error="Error with token: AIzaSy123456789012345678901234567890123",
                )

        registry.register(SecretLeakingTool())
        executor = ToolExecutor(registry=registry)

        call = ToolCall(tool_call_id="s1", tool_name="leak_secret")
        res = executor.execute_tool(call)

        self.assertNotIn("sk-123456789012345678901234", str(res.output))
        self.assertNotIn("AIzaSy123456789012345678901234567890123", str(res.error))

    def test_web_search_tool_provider(self):
        class MockProvider(WebResearchProvider):
            def search(self, request: WebResearchRequest) -> WebResearchResponse:
                return WebResearchResponse(
                    results=[{
                        "title": "AI News Today",
                        "url": "https://example.com/news",
                        "snippet": "Latest breakthroughs in AI.",
                        "source": "web",
                    }],
                    provider_name="mock_search",
                )

        search_tool = WebSearchTool(provider=MockProvider())
        call = ToolCall(tool_call_id="ws1", tool_name="web_search", arguments={"query": "AI news"})
        res = search_tool.execute(call)

        self.assertEqual(res.status, ToolExecutionStatus.SUCCESS)
        self.assertEqual(len(res.output["results"]), 1)
        self.assertEqual(res.output["results"][0]["url"], "https://example.com/news")

    def test_web_fetch_ssrf_protection(self):
        fetch_provider = WebFetchProvider()

        with self.assertRaises(ValueError):
            fetch_provider.validate_url_ssrf("http://127.0.0.1:8080/admin")

        with self.assertRaises(ValueError):
            fetch_provider.validate_url_ssrf("http://localhost/secret")

        with self.assertRaises(ValueError):
            fetch_provider.validate_url_ssrf("http://10.0.0.1/internal")

    def test_agent_routing_and_planning_phase7(self):
        router = AgentRouter()
        planner = AgentPlanner()

        # This test exercises the deterministic compatibility router explicitly.
        # The production default is LLM-driven tool selection, so the legacy
        # keyword router must never be inferred from the default mode.
        deterministic = {"llm_driven_tools": False}

        req_calc = AgentRequest(
            request_id="r1",
            conversation_id="c1",
            message="Calculate 1847 * 392",
            execution_config=deterministic,
        )
        route_calc = router.route_request(req_calc)
        self.assertEqual(route_calc, AgentRoute.TOOL)

        plan_calc = planner.create_plan(req_calc, route_calc)
        self.assertTrue(plan_calc.tool_required)
        self.assertIn("TOOL_EXECUTION", plan_calc.steps)

        req_research = AgentRequest(
            request_id="r2",
            conversation_id="c1",
            message="Search web for latest AI news",
            execution_config=deterministic,
        )
        route_research = router.route_request(req_research)
        self.assertEqual(route_research, AgentRoute.RESEARCH)

        plan_research = planner.create_plan(req_research, route_research)
        self.assertTrue(plan_research.tool_required)
        self.assertTrue(plan_research.retrieval_required)

    def test_agent_router_defaults_to_llm_driven_tools(self):
        router = AgentRouter()
        request = AgentRequest(
            request_id="r3",
            conversation_id="c1",
            message="Calculate 1847 * 392",
        )
        self.assertEqual(router.route_request(request), AgentRoute.DIRECT)


if __name__ == "__main__":
    unittest.main()
