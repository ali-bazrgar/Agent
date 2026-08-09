from superagent.agents.models import VerificationStatus
from superagent.agents.verifier import AgentVerifier


def test_agent_verifier_supported():
    verifier = AgentVerifier()
    provenance = [{"chunk_id": "chunk-1", "score": 0.9, "content": "Python is a programming language used to build software and automate tasks."}]
    res = verifier.verify(
        query="What is Python?",
        candidate_answer="Python is a programming language.",
        context_provenance=provenance,
    )
    assert res.verified is True
    assert res.status == VerificationStatus.SUPPORTED
    assert res.supported_claims


def test_agent_verifier_no_provenance_is_not_verified():
    verifier = AgentVerifier()
    res = verifier.verify(
        query="What is Python?",
        candidate_answer="Python is a programming language.",
        context_provenance=[],
    )
    assert res.verified is False
    assert res.status == VerificationStatus.UNKNOWN
    assert res.unsupported_claims


def test_agent_verifier_rejects_unrelated_evidence():
    verifier = AgentVerifier()
    res = verifier.verify(
        query="What is Python?",
        candidate_answer="Python was created as a database engine for relational queries.",
        context_provenance=[{"chunk_id": "chunk-1", "score": 0.9, "content": "Python is a programming language used for scripting and software development."}],
    )
    assert res.verified is False
    assert res.status == VerificationStatus.UNSUPPORTED
    assert res.unsupported_claims
