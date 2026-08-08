from superagent.agents.critic import AgentCritic
from superagent.agents.models import AgentExecutionStatus, AgentRequest, CritiqueResult
from superagent.agents.orchestrator import AgentOrchestrator
from superagent.providers.contracts import LLMProvider, LLMRequest, LLMResponse, ProviderHealth, ProviderHealthStatus, ProviderCapabilities


class MockRevisionLLM(LLMProvider):
    def __init__(self) -> None:
        self.call_count = 0

    def complete(self, request: LLMRequest) -> LLMResponse:
        self.call_count += 1
        if self.call_count == 1:
            return LLMResponse(text="Wrong answer", model_id="mock-llm")
        return LLMResponse(text="Correct answer on revision", model_id="mock-llm")

    def check_health(self) -> ProviderHealth:
        return ProviderHealth(name="mock", status=ProviderHealthStatus.HEALTHY)

    def capabilities(self) -> ProviderCapabilities:
        return ProviderCapabilities(chat=True)


class FlakyCritic(AgentCritic):
    def __init__(self) -> None:
        super().__init__()
        self.calls = 0

    def critique(self, query: str, context_str: str, response_text: str) -> CritiqueResult:
        self.calls += 1
        if self.calls == 1:
            return CritiqueResult(
                passed=False,
                score=0.3,
                issues=["Answer is incomplete"],
                required_revision="Elaborate details",
            )
        return CritiqueResult(passed=True, score=1.0)


def test_orchestrator_bounded_revision_loop():
    llm = MockRevisionLLM()
    critic = FlakyCritic()
    orchestrator = AgentOrchestrator(llm_provider=llm, critic=critic)

    req = AgentRequest(
        request_id="req-rev",
        conversation_id="conv-rev",
        message="Explain quantum computing",
        execution_config={"max_iterations": 2},
    )

    res = orchestrator.execute(req)

    assert res.status == AgentExecutionStatus.COMPLETED
    assert res.answer == "Correct answer on revision"
    assert res.iterations == 2
    assert llm.call_count == 2
