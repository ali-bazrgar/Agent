from __future__ import annotations

from abc import ABC, abstractmethod
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field

from superagent.llm.capabilities import CapabilitySet


class ProviderHealthStatus(str, Enum):
    HEALTHY = "healthy"
    UNAVAILABLE = "unavailable"
    MISCONFIGURED = "misconfigured"
    UNKNOWN = "unknown"


class ProviderHealth(BaseModel):
    name: str
    status: ProviderHealthStatus
    message: str | None = None
    details: dict[str, Any] = Field(default_factory=dict)


class ProviderCapabilities(CapabilitySet):
    """Provider-level capabilities using the canonical capability vocabulary."""

    pass


class LLMRequest(BaseModel):
    """Provider-neutral completion request.

    Generation controls belong to the request contract rather than to a concrete
    provider implementation. Providers may omit unsupported optional controls,
    but must never silently reinterpret them.
    """

    prompt: str = Field(min_length=1)
    system_prompt: str | None = None
    messages: list[dict[str, Any]] = Field(default_factory=list)
    tools: list[dict[str, Any]] = Field(default_factory=list)
    tool_choice: str | dict[str, Any] = "auto"
    max_tokens: int | None = Field(default=None, ge=1)
    temperature: float | None = Field(default=None, ge=0.0, le=2.0)
    top_p: float | None = Field(default=None, gt=0.0, le=1.0)
    frequency_penalty: float | None = Field(default=None, ge=-2.0, le=2.0)
    presence_penalty: float | None = Field(default=None, ge=-2.0, le=2.0)
    seed: int | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class LLMToolCall(BaseModel):
    id: str = Field(min_length=1)
    name: str = Field(min_length=1)
    arguments: dict[str, Any] = Field(default_factory=dict)


class LLMResponse(BaseModel):
    text: str = ""
    model_id: str | None = None
    token_usage: int | None = None
    provider_name: str | None = None
    finish_reason: str | None = None
    tool_calls: list[LLMToolCall] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)


class EmbeddingRequest(BaseModel):
    texts: list[str] = Field(default_factory=list)


class EmbeddingResponse(BaseModel):
    embeddings: list[list[float]]
    provider_name: str | None = None


class RerankRequest(BaseModel):
    query: str = Field(min_length=1)
    candidates: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)


class RerankResponse(BaseModel):
    ranked_items: list[dict[str, Any]]
    provider_name: str | None = None


class WebResearchRequest(BaseModel):
    query: str = Field(min_length=1)
    max_results: int = Field(default=5, ge=1)
    metadata: dict[str, Any] = Field(default_factory=dict)


class WebResearchResponse(BaseModel):
    results: list[dict[str, Any]]
    provider_name: str | None = None


class LLMProvider(ABC):
    @abstractmethod
    def complete(self, request: LLMRequest) -> LLMResponse: ...

    @abstractmethod
    def check_health(self) -> ProviderHealth: ...

    @abstractmethod
    def capabilities(self) -> ProviderCapabilities: ...


class EmbeddingProvider(ABC):
    @abstractmethod
    def embed(self, request: EmbeddingRequest) -> EmbeddingResponse: ...

    @abstractmethod
    def check_health(self) -> ProviderHealth: ...

    @abstractmethod
    def capabilities(self) -> ProviderCapabilities: ...


class RerankerProvider(ABC):
    @abstractmethod
    def rerank(self, request: RerankRequest) -> RerankResponse: ...

    @abstractmethod
    def check_health(self) -> ProviderHealth: ...

    @abstractmethod
    def capabilities(self) -> ProviderCapabilities: ...


class WebResearchProvider(ABC):
    @abstractmethod
    def search(self, request: WebResearchRequest) -> WebResearchResponse: ...
