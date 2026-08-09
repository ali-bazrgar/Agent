import pytest

from superagent.agents.models import AgentExecutionStatus
from superagent.agents.state import AgentStateMachine, ExecutionBudgetExceeded


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


def test_model_call_is_reserved_before_provider_invocation():
    sm = AgentStateMachine(execution_id="exec-model", request_id="req-model", max_model_calls=1)
    sm.reserve_model_call()
    assert sm.model_calls == 1
    with pytest.raises(ExecutionBudgetExceeded):
        sm.reserve_model_call()


def test_tool_call_is_reserved_before_tool_invocation():
    sm = AgentStateMachine(execution_id="exec-tool", request_id="req-tool", max_tool_calls=1)
    sm.reserve_tool_call()
    assert sm.tool_calls == 1
    with pytest.raises(ExecutionBudgetExceeded):
        sm.reserve_tool_call()


def test_model_token_budget_is_cumulative_and_persisted_in_diagnostics():
    sm = AgentStateMachine(execution_id="exec-tokens", request_id="req-tokens", max_total_model_tokens=100)
    sm.record_model_usage(40)
    sm.record_model_usage(50)
    assert sm.model_tokens == 90
    assert sm.diagnostics["token_usage"] == {"total": 90, "budget": 100, "exceeded": False}

    with pytest.raises(ExecutionBudgetExceeded):
        sm.record_model_usage(11)
    assert sm.model_tokens == 101
    assert sm.diagnostics["token_usage"]["exceeded"] is True
