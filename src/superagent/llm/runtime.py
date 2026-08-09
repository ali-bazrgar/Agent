from __future__ import annotations

from pydantic import BaseModel, Field

from superagent.llm.capabilities import EffectiveCapabilities


class ModelRuntimeConfig(BaseModel):
    """Provider-neutral runtime configuration.

    ``context_window_tokens`` is the *actual runtime context* requested for the
    model, while ``max_output_tokens`` is only an optional generation cap.  A
    missing output cap is intentional: the provider/model may use its own
    maximum instead of the application silently imposing a small ceiling.
    """

    model_id: str | None = None
    context_window_tokens: int = Field(default=8192, ge=256)
    max_output_tokens: int | None = Field(default=None, ge=1)
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
        reserved = self.max_output_tokens or 0
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
