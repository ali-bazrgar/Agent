from __future__ import annotations

from pydantic import BaseModel, Field

from superagent.llm.capabilities import EffectiveCapabilities


class ContextAllocationPolicy(BaseModel):
    """Controls how the fixed model context is allocated at request time.

    The runtime context is intentionally fixed by the user/model profile.  This
    policy does *not* shrink that context. It tells the orchestration layer how
    aggressively to populate it with conversation, memory and knowledge before
    sending the request to the LLM.
    """

    use_conversation_history: bool = True
    use_memory: bool = True
    use_knowledge: bool = True
    max_memory_tokens: int | None = Field(default=None, ge=0)
    max_knowledge_tokens: int | None = Field(default=None, ge=0)
    max_history_tokens: int | None = Field(default=None, ge=0)
    min_retrieval_score: float | None = Field(default=None, ge=0.0, le=1.0)
    reserve_output_tokens: int = Field(default=0, ge=0)

    def available_context_tokens(self, context_window_tokens: int) -> int:
        """Return the context budget available to prompt construction.

        A value of zero for ``reserve_output_tokens`` means that the model is
        not artificially given a fixed generation reservation. This is the
        default because the user-selected context is the hard runtime ceiling,
        while the model decides how much of the available budget is useful.
        """
        if context_window_tokens < 256:
            raise ValueError("context_window_tokens must be at least 256")
        return max(0, context_window_tokens - self.reserve_output_tokens)


class ModelRuntimeConfig(BaseModel):
    """Provider-neutral runtime configuration.

    ``context_window_tokens`` is the user's fixed runtime context ceiling. It
    is selected once in the model profile (for example 32K or 128K) and remains
    stable for requests. It is deliberately different from generation length:
    the application does not reserve a hidden 1K/2K output budget.

    ``max_output_tokens=None`` means no application-side generation cap is sent
    to the provider. The server/model may then generate until its own stopping
    criteria or the remaining context is exhausted.
    """

    model_id: str | None = None
    context_window_tokens: int = Field(default=8192, ge=256)
    max_output_tokens: int | None = Field(default=None, ge=1)
    temperature: float = Field(default=0.7, ge=0.0, le=2.0)
    top_p: float = Field(default=1.0, gt=0.0, le=1.0)
    timeout_seconds: float = Field(default=60.0, gt=0.0)
    context_allocation: ContextAllocationPolicy = Field(default_factory=ContextAllocationPolicy)

    @classmethod
    def from_effective_capabilities(
        cls,
        capabilities: EffectiveCapabilities,
        *,
        temperature: float = 0.7,
        top_p: float = 1.0,
        timeout_seconds: float = 60.0,
        fallback_context_window_tokens: int = 8192,
        fallback_max_output_tokens: int | None = None,
    ) -> "ModelRuntimeConfig":
        """Resolve runtime limits without inventing a small output ceiling."""
        context = capabilities.context_window_tokens or fallback_context_window_tokens
        configured_output = capabilities.max_output_tokens
        if configured_output is None:
            configured_output = fallback_max_output_tokens
        if configured_output is not None:
            configured_output = min(configured_output, context)
        return cls(
            model_id=capabilities.model_id,
            context_window_tokens=context,
            max_output_tokens=configured_output,
            temperature=temperature,
            top_p=top_p,
            timeout_seconds=timeout_seconds,
        )

    @property
    def available_prompt_tokens(self) -> int:
        """Available prompt budget without an implicit output reservation."""
        reserved = self.max_output_tokens or self.context_allocation.reserve_output_tokens
        return max(0, self.context_window_tokens - reserved)

    def validate_prompt_budget(self, prompt_tokens: int, output_tokens: int | None = None) -> None:
        if prompt_tokens < 0:
            raise ValueError("prompt_tokens must be non-negative")
        reserved = self.max_output_tokens if output_tokens is None else output_tokens
        if reserved is not None and reserved < 1:
            raise ValueError("output_tokens must be positive when provided")
        if reserved is not None and prompt_tokens + reserved > self.context_window_tokens:
            raise ValueError(
                "prompt plus reserved output exceeds model context window: "
                f"{prompt_tokens} + {reserved} > {self.context_window_tokens}"
            )

    def context_budget_for_prompt(self) -> int:
        """Budget exposed to prompt assembly/retrieval for this request."""
        return self.context_allocation.available_context_tokens(self.context_window_tokens)
