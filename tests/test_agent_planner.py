from superagent.agents.models import AgentRequest, AgentRoute
from superagent.agents.planner import AgentPlanner


def test_agent_planner_direct_route_recalls_persistent_memory():
    planner = AgentPlanner()
    req = AgentRequest(request_id="req-1", conversation_id="conv-1", message="Hi")
    plan = planner.create_plan(req, AgentRoute.DIRECT)

    assert plan.route == AgentRoute.DIRECT
    assert plan.max_iterations == 2
    assert plan.retrieval_required is False
    assert plan.memory_required is True
    assert plan.memory_recall_every_message is True
    assert "RETRIEVING" in plan.steps
    assert "GENERATING" in plan.steps


def test_agent_planner_retrieval_route_uses_adaptive_quality_by_default():
    planner = AgentPlanner()
    req = AgentRequest(request_id="req-2", conversation_id="conv-1", message="Search doc")
    plan = planner.create_plan(req, AgentRoute.RETRIEVAL)

    assert plan.retrieval_required is True
    assert plan.memory_required is True
    assert "RETRIEVING" in plan.steps
    assert "VERIFYING" not in plan.steps


def test_agent_planner_can_explicitly_enable_always_verification():
    planner = AgentPlanner()
    req = AgentRequest(
        request_id="req-3",
        conversation_id="conv-1",
        message="Search doc",
        execution_config={"quality_mode": "always"},
    )
    plan = planner.create_plan(req, AgentRoute.RETRIEVAL)

    assert plan.verifier_required is True
    assert "VERIFYING" in plan.steps
