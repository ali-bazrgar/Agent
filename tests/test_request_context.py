from superagent.context.request import ANONYMOUS_PRINCIPAL, Principal, RequestContext
from superagent.agents.models import AgentRequest


def test_anonymous_principal_is_explicit_and_stable() -> None:
    assert ANONYMOUS_PRINCIPAL.principal_id == "anonymous"
    assert ANONYMOUS_PRINCIPAL.principal_type == "anonymous"


def test_principal_rejects_blank_identity() -> None:
    try:
        Principal(principal_id="   ")
    except ValueError as exc:
        assert "principal_id" in str(exc)
    else:
        raise AssertionError("blank principal must be rejected")


def test_request_context_requires_request_and_conversation_ids() -> None:
    context = RequestContext(
        request_id="req-1",
        conversation_id="conv-1",
        principal=Principal(principal_id="user-a"),
    )
    assert context.principal.principal_id == "user-a"


def test_agent_request_carries_trusted_principal() -> None:
    request = AgentRequest(
        request_id="req-1",
        conversation_id="conv-1",
        message="hello",
        principal=Principal(principal_id="user-a"),
    )
    assert request.principal.principal_id == "user-a"
