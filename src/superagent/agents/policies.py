from __future__ import annotations

from typing import Any


class ExecutionPolicy:
    """Configurable execution policies for the orchestrator."""

    def __init__(
        self,
        max_iterations: int = 2,
        allow_revision: bool = True,
        fallback_on_critic_failure: bool = True,
        fallback_on_verifier_failure: bool = True,
        fallback_on_memory_failure: bool = True,
        fallback_on_retrieval_failure: bool = True,
    ) -> None:
        self.max_iterations = max(1, max_iterations)
        self.allow_revision = allow_revision
        self.fallback_on_critic_failure = fallback_on_critic_failure
        self.fallback_on_verifier_failure = fallback_on_verifier_failure
        self.fallback_on_memory_failure = fallback_on_memory_failure
        self.fallback_on_retrieval_failure = fallback_on_retrieval_failure

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ExecutionPolicy:
        return cls(
            max_iterations=data.get("max_iterations", 2),
            allow_revision=data.get("allow_revision", True),
            fallback_on_critic_failure=data.get("fallback_on_critic_failure", True),
            fallback_on_verifier_failure=data.get("fallback_on_verifier_failure", True),
            fallback_on_memory_failure=data.get("fallback_on_memory_failure", True),
            fallback_on_retrieval_failure=data.get("fallback_on_retrieval_failure", True),
        )
