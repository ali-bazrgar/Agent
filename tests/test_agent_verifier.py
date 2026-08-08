from superagent.agents.models import VerificationStatus
from superagent.agents.verifier import AgentVerifier


def test_agent_verifier_supported():
    verifier = AgentVerifier()
    provenance = [{"chunk_id": "chunk-1", "score": 0.9}]
    res = verifier.verify(
        query="What is Python?",
        candidate_answer="Python is a programming language.",
        context_provenance=provenance,
    )
    assert res.verified is True
    assert res.status == VerificationStatus.SUPPORTED


def test_agent_verifier_no_provenance():
    verifier = AgentVerifier()
    res = verifier.verify(
        query="What is Python?",
        candidate_answer="Python is a programming language.",
        context_provenance=[],
    )
    assert res.verified is True
    assert res.status == VerificationStatus.UNKNOWN
