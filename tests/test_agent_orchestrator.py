from unittest.mock import MagicMock

from superagent.agents.models import AgentExecutionStatus, AgentRequest
from superagent.agents.orchestrator import AgentOrchestrator
from superagent.providers.contracts import LLMProvider, LLMRequest, LLMResponse, ProviderHealth, ProviderHealthStatus, ProviderCapabilities


class MockLLM(LLMProvider):
    def complete(self, request: LLMRequest) -> LLMResponse:
        return LLMResponse(text="Paris is the capital of France.", model_id="mock-llm")

    def check_health(self) -> ProviderHealth:
        return ProviderHealth(name="mock", status=ProviderHealthStatus.HEALTHY)

    def capabilities(self) -> ProviderCapabilities:
        return ProviderCapabilities(chat=True)


def test_orchestrator_direct_execution():
    llm = MockLLM()
    orchestrator = AgentOrchestrator(llm_provider=llm)

    req = AgentRequest(
        request_id="req-1",
        conversation_id="conv-1",
        message="What is the capital of France?",
    )

    res = orchestrator.execute(req)

    assert res.status == AgentExecutionStatus.COMPLETED
    assert res.answer == "Paris is the capital of France."
    assert res.iterations == 1
    assert res.used_retrieval is False
