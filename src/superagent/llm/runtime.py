from __future__ import annotations

from pydantic import BaseModel, Field

from superagent.llm.capabilities import EffectiveCapabilities


class ModelRuntimeConfig(BaseModel):
    """Provider-neutral model/runtime limits used by both context planning and runtimes."""

    model_id: str | None = None
    context_window_tokens: int = Field(default=8192, ge=256)
    max_output_tokens: int | None = Field(default=1024, ge=1)
    temperature: float = Field(default=0.7, ge=0.0, le=2.0)
    top_p: float = Field(default=1.0, gt=0.0, le=1.0)
    timeout_seconds: float = Field(default=60.0, gt=0.0)

    @classmethod
    def from_effective_capabilities(
        cls,
        capabilities: EffectiveCapabilities,
        *,
        temperature: float = 0.7,
        top_p: float = 1.0,
        timeout_seconds: float = 60.0,
        fallback_context_window_tokens: int = 8192,
        fallback_max_output_tokens: int | None = 1024,
    ) -> "ModelRuntimeConfig":
        """Build runtime limits from already-resolved model/provider capabilities.

        The effective capability intersection is authoritative. Fallbacks are used
        only when a provider/model does not publish a limit, preventing an arbitrary
        hard-coded context size from overriding known capability metadata.
        """
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
        """Tokens available for input after reserving the configured output budget."""
        reserved = self.max_output_tokens or 0
        return max(0, self.context_window_tokens - reserved)

    def validate_prompt_budget(self, prompt_tokens: int, output_tokens: int | None = None) -> None:
        """Reject a request whose input plus reserved output exceeds the model context."""
        if prompt_tokens < 0:
            raise ValueError("prompt_tokens must be non-negative")
        reserved = self.max_output_tokens if output_tokens is None else output_tokens
        if reserved is not None and reserved < 1:
            raise ValueError("output_tokens must be positive when provided")
        if prompt_tokens + (reserved or 0) > self.context_window_tokens:
            raise ValueError(
                "prompt plus reserved output exceeds model context window: "
                f"{prompt_tokens} + {reserved or 0} > {self.context_window_tokens}"
            )
