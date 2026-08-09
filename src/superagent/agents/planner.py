from superagent.agents.models import AgentRequest, AgentRoute, ExecutionPlan
from superagent.agents.ports import AgentPlannerPort


class AgentPlanner(AgentPlannerPort):
    """Planner for bounded execution; semantic tool choice belongs to the LLM.

    Quality checks are adaptive by default: a plain conversational turn should
    not trigger extra LLM generations, while retrieval/tool-heavy turns can opt
    into critique/verification. ``quality_mode=always`` preserves explicit
    always-check behavior.
    """

    def create_plan(self, request: AgentRequest, route: AgentRoute) -> ExecutionPlan:
        max_iters = request.execution_config.get("max_iterations", 2)
        if not isinstance(max_iters, int) or max_iters < 1:
            max_iters = 2

        quality_mode = str(request.execution_config.get("quality_mode", "auto")).strip().lower()
        if quality_mode not in {"auto", "always", "off"}:
            quality_mode = "auto"

        critic_override = request.execution_config.get("critic_required")
        verifier_override = request.execution_config.get("verifier_required")
        critic_req = bool(critic_override) if isinstance(critic_override, bool) else quality_mode == "always"
        verifier_req = bool(verifier_override) if isinstance(verifier_override, bool) else quality_mode == "always"
        llm_driven_tools = bool(request.execution_config.get("llm_driven_tools", True))
        memory_recall_every_message = bool(request.execution_config.get("memory_recall_every_message", True))

        steps: list[str] = ["ROUTING", "PLANNING"]
        retrieval_required = route in (AgentRoute.RETRIEVAL, AgentRoute.RETRIEVAL_AND_MEMORY, AgentRoute.RESEARCH_READY, AgentRoute.RESEARCH)
        memory_required = memory_recall_every_message or route in (AgentRoute.MEMORY, AgentRoute.RETRIEVAL_AND_MEMORY)

        tool_required = route in (AgentRoute.TOOL, AgentRoute.RESEARCH) and not llm_driven_tools
        if llm_driven_tools or tool_required:
            steps.append("TOOL_EXECUTION")
        if retrieval_required or memory_required:
            steps.append("RETRIEVING")

        steps.extend(["CONTEXT_BUILDING", "GENERATING"])
        if critic_req:
            steps.append("CRITIQUING")
        verifier_enabled = verifier_req and (retrieval_required or tool_required or llm_driven_tools)
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
            critic_required=critic_req,
            verifier_required=verifier_enabled,
            revision_allowed=True,
        )
