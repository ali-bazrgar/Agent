from superagent.agents.models import AgentExecutionStatus
from superagent.agents.state import AgentStateMachine


def test_agent_state_machine_transitions():
    sm = AgentStateMachine(execution_id="exec-123", request_id="req-123")
    assert sm.current_status == AgentExecutionStatus.CREATED

    sm.transition_to(AgentExecutionStatus.ROUTING)
    assert sm.current_status == AgentExecutionStatus.ROUTING
    assert len(sm.steps) == 1
    assert sm.steps[0].step_name == "routing"

    sm.transition_to(AgentExecutionStatus.COMPLETED)
    assert sm.completed_at is not None
    domain_state = sm.to_domain_state()
    assert domain_state.status == "completed"
