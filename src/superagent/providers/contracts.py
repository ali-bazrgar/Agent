from __future__ import annotations

from abc import ABC, abstractmethod
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


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


class ProviderCapabilities(BaseModel):
    chat: bool = False
    streaming: bool = False
    embedding: bool = False
    batch_embedding: bool = False
    reranking: bool = False
    structured_output: bool = False
    tool_calling: bool = False
    multimodal: bool = False
    image_input: bool = False
    audio_input: bool = False
    video_input: bool = False
    context_size: int | None = None


class LLMRequest(BaseModel):
    """Provider-neutral completion request with OpenAI-compatible multimodal content."""

    prompt: str = Field(min_length=1)
    system_prompt: str | None = None
    messages: list[dict[str, Any]] = Field(default_factory=list)
    max_tokens: int | None = Field(default=None, ge=1)
    temperature: float | None = Field(default=None, ge=0.0, le=2.0)
    metadata: dict[str, Any] = Field(default_factory=dict)


class LLMResponse(BaseModel):
    text: str
    model_id: str | None = None
    token_usage: int | None = None
    provider_name: str | None = None
    finish_reason: str | None = None


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
