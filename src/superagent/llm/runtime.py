from __future__ import annotations

from pydantic import BaseModel, Field


class ModelRuntimeConfig(BaseModel):
    """Provider-neutral model/runtime limits used by both context planning and runtimes."""

    model_id: str | None = None
    context_window_tokens: int = Field(default=8192, ge=256)
    max_output_tokens: int | None = Field(default=1024, ge=1)
    temperature: float = Field(default=0.7, ge=0.0, le=2.0)
    top_p: float = Field(default=1.0, gt=0.0, le=1.0)
    timeout_seconds: float = Field(default=60.0, gt=0.0)

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
