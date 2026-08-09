from superagent.agents.state import AgentStateMachine, ExecutionBudgetExceeded
from superagent.config.settings import get_settings


def test_state_machine_loads_application_execution_budgets():
    settings = get_settings()
    state = AgentStateMachine("exec-budget-test")
    assert state.max_model_calls == settings.max_model_calls
    assert state.max_tool_calls == settings.max_tool_calls
    assert state.max_retries == settings.max_retries
    assert state.max_execution_time_seconds == settings.max_execution_time_seconds


def test_explicit_execution_budget_override_is_preserved():
    state = AgentStateMachine("exec-override-test", max_model_calls=1, max_tool_calls=2, max_retries=0, max_execution_time_seconds=10)
    assert state.max_model_calls == 1
    assert state.max_tool_calls == 2
    assert state.max_retries == 0
    assert state.max_execution_time_seconds == 10
    state.increment_model_calls()
    try:
        state.increment_model_calls()
    except ExecutionBudgetExceeded:
        pass
    else:
        raise AssertionError("model-call budget was not enforced")
