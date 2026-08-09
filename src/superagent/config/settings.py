from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Any, Literal

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Typed application settings backed by environment variables and .env files."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        env_prefix="SUPERAGENT_",
        case_sensitive=False,
        extra="ignore",
    )

    environment: Literal["development", "testing", "production"] = Field(default="development")
    debug: bool = Field(default=False)
    app_host: str = Field(default="127.0.0.1")
    app_port: int = Field(default=8000)
    log_level: str = Field(default="INFO")

    database_path: Path = Field(default=Path("data/superagent.sqlite3"))
    storage_path: Path = Field(default=Path("data/storage"))

    # LLM provider is intentionally OpenAI-compatible rather than llama.cpp-specific.
    llm_provider: Literal["openai_compatible", "llama_cpp"] = Field(default="openai_compatible")
    llm_base_url: str = Field(default="http://127.0.0.1:8080")
    llm_chat_completions_path: str = Field(default="/v1/chat/completions")
    llm_health_path: str = Field(default="/health")
    llm_model_id: str | None = Field(default=None)
    provider_api_key: str | None = Field(default=None)
    llm_temperature: float = Field(default=0.7, ge=0.0, le=2.0)
    llm_max_output_tokens: int | None = Field(default=1024, ge=1)
    context_window_tokens: int = Field(default=8192, ge=256)
    tools_enabled: bool = Field(default=True)
    structured_output_enabled: bool = Field(default=True)
    # JSON object keyed by concrete model id. Example:
    # {"gemma": {"context_window_tokens": 32768, "tool_calling": true}}
    model_capability_overrides: dict[str, dict[str, Any]] = Field(default_factory=dict)

    embedding_base_url: str = Field(default="http://127.0.0.1:8081")
    reranker_base_url: str = Field(default="http://127.0.0.1:8082")
    embedding_model_id: str | None = Field(default=None)
    reranker_model_id: str | None = Field(default=None)
    provider_connect_timeout_seconds: float = Field(default=5.0, gt=0)
    provider_read_timeout_seconds: float = Field(default=30.0, gt=0)
    provider_total_timeout_seconds: float = Field(default=60.0, gt=0)
    provider_retry_count: int = Field(default=2, ge=0)
    provider_retry_backoff_seconds: float = Field(default=0.5, ge=0)

    web_provider: str = Field(default="stub")
    web_provider_base_url: str | None = Field(default=None)

    max_model_calls: int = Field(default=4, ge=1)
    max_tool_calls: int = Field(default=8, ge=0)
    max_retries: int = Field(default=2, ge=0)
    max_execution_time_seconds: int = Field(default=60, ge=1)

    learning_enabled: bool = Field(default=True)
    daily_review_limit: int = Field(default=50)
    new_cards_per_day: int = Field(default=20)
    max_generated_cards: int = Field(default=5)
    learning_context_budget: int = Field(default=1500)

    @field_validator("llm_base_url", "embedding_base_url", "reranker_base_url")
    @classmethod
    def validate_base_url(cls, value: str) -> str:
        value = value.strip().rstrip("/")
        if not value.startswith(("http://", "https://")):
            raise ValueError("provider base URL must start with http:// or https://")
        return value

    @field_validator("llm_chat_completions_path", "llm_health_path")
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


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return a cached settings instance for the process."""

    return Settings()
