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
        memory_recall_every_message = bool(request.execution_config.get("memory_recall_every_message", True))

        steps: list[str] = ["ROUTING", "PLANNING"]

        retrieval_required = route in (AgentRoute.RETRIEVAL, AgentRoute.RETRIEVAL_AND_MEMORY, AgentRoute.RESEARCH_READY, AgentRoute.RESEARCH)
        # Persistent memory is an infrastructure capability: by default it is
        # recalled on every user message. Explicit memory routes remain supported.
        memory_required = memory_recall_every_message or route in (AgentRoute.MEMORY, AgentRoute.RETRIEVAL_AND_MEMORY)

        # In agentic mode, tool execution is a capability made available to the
        # model, not an instruction inferred from the route. The model may select
        # zero or more tools and the bounded provider loop executes those calls.
        tool_required = route in (AgentRoute.TOOL, AgentRoute.RESEARCH) and not llm_driven_tools
        if llm_driven_tools or tool_required:
            steps.append("TOOL_EXECUTION")

        if retrieval_required or memory_required:
            steps.append("RETRIEVING")

        steps.extend(["CONTEXT_BUILDING", "GENERATING"])
        if critic_req:
            steps.append("CRITIQUING")

        verifier_enabled = bool(verifier_req) and (retrieval_required or tool_required or llm_driven_tools)
        if verifier_enabled:
            steps.append("VERIFYING")

        steps.extend(["MEMORY_PROCESSING", "COMPLETED"])
        return ExecutionPlan(
            route=route,
            steps=steps,
            max_iterations=max_iters,
            retrieval_required=retrieval_required,
            memory_required=memory_required,
            tool_required=tool_required,
            critic_required=bool(critic_req),
            verifier_required=verifier_enabled,
            revision_allowed=True,
        )
