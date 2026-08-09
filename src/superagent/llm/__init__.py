"""LLM provider adapters.

Adapters are imported lazily so importing provider contracts or capability
models does not initialize every optional LLM implementation.
"""

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .llama_cpp_provider import LlamaCppLLMProvider
    from .openai_compatible_provider import OpenAICompatibleLLMProvider

__all__ = ["LlamaCppLLMProvider", "OpenAICompatibleLLMProvider"]


def __getattr__(name: str):
    if name == "LlamaCppLLMProvider":
        from .llama_cpp_provider import LlamaCppLLMProvider

        return LlamaCppLLMProvider
    if name == "OpenAICompatibleLLMProvider":
        from .openai_compatible_provider import OpenAICompatibleLLMProvider

        return OpenAICompatibleLLMProvider
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
