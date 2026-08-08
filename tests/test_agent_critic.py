from superagent.agents.critic import AgentCritic


def test_agent_critic_valid_response():
    critic = AgentCritic()
    res = critic.critique(
        query="What is the capital of France?",
        context_str="France capital is Paris.",
        response_text="The capital of France is Paris.",
    )
    assert res.passed is True
    assert res.score == 1.0


def test_agent_critic_empty_response():
    critic = AgentCritic()
    res = critic.critique(
        query="What is the capital of France?",
        context_str="Paris is capital.",
        response_text="",
    )
    assert res.passed is False
    assert res.score == 0.0
    assert "Response text is empty." in res.issues
