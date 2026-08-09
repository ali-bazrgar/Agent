from __future__ import annotations

from superagent.agents.models import AgentRequest, AgentRoute, ExecutionPlan
from superagent.agents.ports import AgentPlannerPort


class AgentPlanner(AgentPlannerPort):
    """Planner for bounded execution; semantic tool choice belongs to the LLM."""

    def create_plan(self, request: AgentRequest, route: AgentRoute) -> ExecutionPlan:
        max_iters = request.execution_config.get("max_iterations", 2)
        if not isinstance(max_iters, int) or max_iters < 1:
            max_iters = 2

        critic_req = request.execution_config.get("critic_required", True)
        verifier_req = request.execution_config.get("verifier_required", True)
        llm_driven_tools = bool(request.execution_config.get("llm_driven_tools", True))
        llm_driven_memory = bool(request.execution_config.get("llm_driven_memory", True))

        steps: list[str] = ["ROUTING", "PLANNING"]

        retrieval_required = route in (
            AgentRoute.RETRIEVAL,
            AgentRoute.RETRIEVAL_AND_MEMORY,
            AgentRoute.RESEARCH_READY,
            AgentRoute.RESEARCH,
        )
        memory_required = (not llm_driven_memory) and route in (
            AgentRoute.MEMORY,
            AgentRoute.RETRIEVAL_AND_MEMORY,
        )

        # tool_required describes the route's tool-capable intent for planning,
        # not permission for the orchestrator to invent a concrete tool call.
        # The execution phase remains part of the plan in both modes. In
        # LLM-driven mode it represents the provider's tool-calling phase and
        # the LLM's selected tool, rather than deterministic text routing.
        tool_required = route in (AgentRoute.TOOL, AgentRoute.RESEARCH)
        if tool_required:
            steps.append("TOOL_EXECUTION")

        if retrieval_required or memory_required:
            steps.append("RETRIEVING")

        steps.extend(["CONTEXT_BUILDING", "GENERATING"])

        if critic_req:
            steps.append("CRITIQUING")
        if verifier_req and (retrieval_required or tool_required):
            steps.append("VERIFYING")

        steps.extend(["MEMORY_PROCESSING", "COMPLETED"])

        return ExecutionPlan(
            route=route,
            steps=steps,
            max_iterations=max_iters,
            retrieval_required=retrieval_required,
            memory_required=memory_required,
            tool_required=tool_required,
            critic_required=critic_req,
            verifier_required=verifier_req and (retrieval_required or tool_required),
            revision_allowed=True,
        )
