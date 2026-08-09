from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Any, Literal

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Typed application settings backed by environment variables and .env files."""

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", env_prefix="SUPERAGENT_", case_sensitive=False, extra="ignore")

    environment: Literal["development", "testing", "production"] = "development"
    debug: bool = False
    app_host: str = "127.0.0.1"
    app_port: int = 8000
    log_level: str = "INFO"
    database_path: Path = Path("data/superagent.sqlite3")
    storage_path: Path = Path("data/storage")

    llm_provider: str = Field(default="openai_compatible", min_length=1)
    llm_base_url: str = "http://127.0.0.1:8080"
    llm_chat_completions_path: str = "/v1/chat/completions"
    llm_health_path: str = "/health"
    llm_model_id: str | None = None
    provider_api_key: str | None = None
    llm_temperature: float = Field(default=0.7, ge=0.0, le=2.0)
    llm_top_p: float = Field(default=1.0, gt=0.0, le=1.0)
    llm_frequency_penalty: float = Field(default=0.0, ge=-2.0, le=2.0)
    llm_presence_penalty: float = Field(default=0.0, ge=-2.0, le=2.0)
    llm_seed: int | None = None
    # None means no application-side generation ceiling. A ceiling may still be
    # explicitly selected per model/runtime profile when desired.
    llm_max_output_tokens: int | None = Field(default=None, ge=1)
    context_window_tokens: int = Field(default=8192, ge=256)
    tools_enabled: bool = True
    structured_output_enabled: bool = True
    require_verified_capabilities: bool = False
    model_capability_overrides: dict[str, dict[str, Any]] = Field(default_factory=dict)
    llm_driven_tools: bool = True
    llm_driven_memory: bool = True
    automatic_memory_extraction_enabled: bool = False

    embedding_base_url: str = "http://127.0.0.1:8081"
    embedding_path: str = "/v1/embeddings"
    embedding_health_path: str = "/health"
    embedding_model_id: str | None = None
    embedding_dimensions: int | None = Field(default=None, ge=1)

    reranker_base_url: str = "http://127.0.0.1:8082"
    reranker_path: str = "/v1/rerank"
    reranker_health_path: str = "/health"
    reranker_model_id: str | None = None
    reranker_top_n: int | None = Field(default=None, ge=1)

    provider_connect_timeout_seconds: float = Field(default=5.0, gt=0)
    provider_read_timeout_seconds: float = Field(default=30.0, gt=0)
    provider_total_timeout_seconds: float = Field(default=60.0, gt=0)
    provider_retry_count: int = Field(default=2, ge=0)
    provider_retry_backoff_seconds: float = Field(default=0.5, ge=0)

    web_provider: str = "stub"
    web_provider_base_url: str | None = None
    max_model_calls: int = Field(default=4, ge=1)
    max_tool_calls: int = Field(default=8, ge=0)
    max_retries: int = Field(default=2, ge=0)
    max_execution_time_seconds: int = Field(default=60, ge=1)
    max_total_model_tokens: int = Field(default=32768, ge=1)
    learning_enabled: bool = True
    daily_review_limit: int = 50
    new_cards_per_day: int = 20
    max_generated_cards: int = 5
    learning_context_budget: int = 1500

    @field_validator("llm_base_url", "embedding_base_url", "reranker_base_url")
    @classmethod
    def validate_base_url(cls, value: str) -> str:
        value = value.strip().rstrip("/")
        if not value.startswith(("http://", "https://")):
            raise ValueError("provider base URL must start with http:// or https://")
        return value

    @field_validator("llm_provider")
    @classmethod
    def validate_provider_id(cls, value: str) -> str:
        value = value.strip().lower()
        if not value:
            raise ValueError("llm provider id must not be empty")
        return value

    @field_validator("llm_chat_completions_path", "llm_health_path", "embedding_path", "embedding_health_path", "reranker_path", "reranker_health_path")
    @classmethod
    def validate_api_path(cls, value: str) -> str:
        value = value.strip()
        return value if value.startswith("/") else f"/{value}"

    @property
    def database_path_resolved(self) -> Path:
        return self.database_path if self.database_path.is_absolute() else Path.cwd() / self.database_path

    @property
    def storage_path_resolved(self) -> Path:
        return self.storage_path if self.storage_path.is_absolute() else Path.cwd() / self.storage_path

    def model_runtime_config(self):
        from superagent.llm.runtime import ModelRuntimeConfig
        return ModelRuntimeConfig(model_id=self.llm_model_id, context_window_tokens=self.context_window_tokens, max_output_tokens=self.llm_max_output_tokens, temperature=self.llm_temperature, top_p=self.llm_top_p, timeout_seconds=self.provider_total_timeout_seconds)


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
