from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import Field
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

    llm_base_url: str = Field(default="http://127.0.0.1:8080")
    embedding_base_url: str = Field(default="http://127.0.0.1:8081")
    reranker_base_url: str = Field(default="http://127.0.0.1:8082")
    llm_model_id: str | None = Field(default=None)
    embedding_model_id: str | None = Field(default=None)
    reranker_model_id: str | None = Field(default=None)
    provider_api_key: str | None = Field(default=None)
    provider_connect_timeout_seconds: float = Field(default=5.0)
    provider_read_timeout_seconds: float = Field(default=30.0)
    provider_total_timeout_seconds: float = Field(default=60.0)
    provider_retry_count: int = Field(default=2)
    provider_retry_backoff_seconds: float = Field(default=0.5)

    web_provider: str = Field(default="stub")
    web_provider_base_url: str | None = Field(default=None)

    context_window_tokens: int = Field(default=8192)
    max_model_calls: int = Field(default=4)
    max_tool_calls: int = Field(default=8)
    max_retries: int = Field(default=2)
    max_execution_time_seconds: int = Field(default=60)

    learning_enabled: bool = Field(default=True)
    daily_review_limit: int = Field(default=50)
    new_cards_per_day: int = Field(default=20)
    max_generated_cards: int = Field(default=5)
    learning_context_budget: int = Field(default=1500)

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
