from superagent.agents.models import AgentRequest, AgentRoute
from superagent.agents.router import AgentRouter


def test_agent_router_direct():
    router = AgentRouter()
    req = AgentRequest(
        request_id="req-1",
        conversation_id="conv-1",
        message="Hello, how are you today?",
    )
    route = router.route_request(req)
    assert route == AgentRoute.DIRECT


def test_agent_router_retrieval():
    router = AgentRouter()
    req = AgentRequest(
        request_id="req-2",
        conversation_id="conv-1",
        message="Search knowledge base for document about architecture",
    )
    route = router.route_request(req)
    assert route == AgentRoute.RETRIEVAL


def test_agent_router_memory():
    router = AgentRouter()
    req = AgentRequest(
        request_id="req-3",
        conversation_id="conv-1",
        message="Remember that my favorite language is Python",
    )
    route = router.route_request(req)
    assert route == AgentRoute.MEMORY


def test_agent_router_forced_override():
    router = AgentRouter()
    req = AgentRequest(
        request_id="req-4",
        conversation_id="conv-1",
        message="Hello",
        execution_config={"force_route": "retrieval"},
    )
    route = router.route_request(req)
    assert route == AgentRoute.RETRIEVAL
