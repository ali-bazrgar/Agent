from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Any

from superagent.core.errors import PersistenceError
from superagent.database.config import DatabaseConfig
from superagent.database.schema import get_schema_statements


class DatabaseEngine:
    """Thin SQLite engine wrapper that owns initialization and connections."""

    def __init__(self, config: DatabaseConfig) -> None:
        self.config = config
        self.config.path.parent.mkdir(parents=True, exist_ok=True)

    def connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.config.path, timeout=self.config.timeout_seconds)
        connection.row_factory = sqlite3.Row
        return connection

    def initialize(self) -> None:
        from superagent.database.schema import get_migration_statements

        with self.connect() as connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS schema_migrations (
                    version TEXT PRIMARY KEY,
                    applied_at TEXT NOT NULL
                )
                """
            )
            cursor = connection.execute("SELECT version FROM schema_migrations")
            applied_versions = {row[0] for row in cursor.fetchall()}

            for version, statements in get_migration_statements().items():
                if version not in applied_versions:
                    for statement in statements:
                        connection.execute(statement)
                    connection.execute(
                        "INSERT OR REPLACE INTO schema_migrations (version, applied_at) VALUES (?, ?)",
                        (version, self._utc_now()),
                    )
            connection.commit()

    def record_migration(self, version: str) -> None:
        with self.connect() as connection:
            connection.execute(
                "INSERT OR REPLACE INTO schema_migrations (version, applied_at) VALUES (?, ?)",
                (version, self._utc_now()),
            )
            connection.commit()

    def _utc_now(self) -> str:
        from datetime import datetime, timezone

        return datetime.now(timezone.utc).isoformat()

    @staticmethod
    def to_json(value: Any) -> str | None:
        if value is None:
            return None
        return json.dumps(value)

    @staticmethod
    def from_json(value: str | None) -> Any:
        if value is None:
            return None
        return json.loads(value)

    def ensure_ready(self) -> None:
        try:
            self.initialize()
        except sqlite3.Error as exc:  # pragma: no cover - defensive path
            raise PersistenceError(f"database initialization failed: {exc}") from exc
