from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from superagent.config.settings import Settings


@dataclass(slots=True)
class DatabaseConfig:
    """Configuration for the SQLite-backed persistence layer."""

    path: Path
    timeout_seconds: float = 30.0

    @classmethod
    def from_settings(cls, settings: Settings) -> "DatabaseConfig":
        return cls(path=settings.database_path_resolved, timeout_seconds=30.0)
