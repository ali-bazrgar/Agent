from superagent.agents.models import AgentRequest, AgentRoute
from superagent.agents.router import AgentRouter


def test_agent_router_direct():
    router = AgentRouter()
    req = AgentRequest(request_id="req-1", conversation_id="conv-1", message="Hello, how are you today?")
    assert router.route_request(req) == AgentRoute.DIRECT


def test_agent_router_does_not_use_language_specific_retrieval_triggers_by_default():
    router = AgentRouter()
    req = AgentRequest(request_id="req-2", conversation_id="conv-1", message="Search knowledge base for document about architecture")
    assert router.route_request(req) == AgentRoute.DIRECT


def test_agent_router_does_not_use_language_specific_memory_triggers_by_default():
    router = AgentRouter()
    req = AgentRequest(request_id="req-3", conversation_id="conv-1", message="Remember that my favorite language is Python")
    assert router.route_request(req) == AgentRoute.DIRECT


def test_agent_router_forced_override():
    router = AgentRouter()
    req = AgentRequest(request_id="req-4", conversation_id="conv-1", message="Hello", execution_config={"force_route": "retrieval"})
    assert router.route_request(req) == AgentRoute.RETRIEVAL


def test_agent_router_legacy_mode_keeps_deterministic_compatibility():
    router = AgentRouter()
    req = AgentRequest(
        request_id="req-5",
        conversation_id="conv-1",
        message="Search knowledge base for architecture",
        execution_config={"llm_driven_tools": False},
    )
    assert router.route_request(req) == AgentRoute.RETRIEVAL
