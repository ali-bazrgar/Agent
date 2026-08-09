from __future__ import annotations

import json
import sqlite3
from typing import Any

from superagent.core.errors import PersistenceError
from superagent.database.config import DatabaseConfig


MEMORY_LIFECYCLE_MIGRATION: tuple[str, ...] = (
    "ALTER TABLE memory_records ADD COLUMN structured_data_json TEXT NOT NULL DEFAULT '{}'",
    "ALTER TABLE memory_records ADD COLUMN classification TEXT NOT NULL DEFAULT 'explicit'",
    "ALTER TABLE memory_records ADD COLUMN last_accessed_at TEXT",
    "ALTER TABLE memory_records ADD COLUMN access_count INTEGER NOT NULL DEFAULT 0",
)


class DatabaseEngine:
    """Thin SQLite engine wrapper that owns initialization and migrations."""

    def __init__(self, config: DatabaseConfig) -> None:
        self.config = config
        self.config.path.parent.mkdir(parents=True, exist_ok=True)

    def connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.config.path, timeout=self.config.timeout_seconds)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        return connection

    def initialize(self) -> None:
        from superagent.database.schema import get_migration_statements
        migrations = dict(get_migration_statements())
        # Version 004 predates the normalized migration table in older local DBs.
        # Keep the same migration identifier but execute ADD COLUMN statements
        # conditionally so a partially upgraded database can recover safely.
        migrations["004_memory_lifecycle_metadata"] = MEMORY_LIFECYCLE_MIGRATION
        with self.connect() as connection:
            connection.execute("CREATE TABLE IF NOT EXISTS schema_migrations (version TEXT PRIMARY KEY, applied_at TEXT NOT NULL)")
            applied_versions = {row[0] for row in connection.execute("SELECT version FROM schema_migrations").fetchall()}
            for version, statements in migrations.items():
                if version in applied_versions:
                    continue
                for statement in statements:
                    self._execute_migration_statement(connection, statement)
                connection.execute("INSERT INTO schema_migrations (version, applied_at) VALUES (?, ?)", (version, self._utc_now()))
            connection.commit()

    @staticmethod
    def _execute_migration_statement(connection: sqlite3.Connection, statement: str) -> None:
        normalized = " ".join(statement.strip().split()).lower()
        if normalized.startswith("alter table memory_records add column "):
            column_name = normalized.split("add column ", 1)[1].split()[0].strip('`"[]')
            columns = {row[1] for row in connection.execute("PRAGMA table_info(memory_records)").fetchall()}
            if column_name in columns:
                return
        connection.execute(statement)

    def record_migration(self, version: str) -> None:
        with self.connect() as connection:
            connection.execute("INSERT OR REPLACE INTO schema_migrations (version, applied_at) VALUES (?, ?)", (version, self._utc_now()))
            connection.commit()

    def _utc_now(self) -> str:
        from datetime import datetime, timezone
        return datetime.now(timezone.utc).isoformat()

    @staticmethod
    def to_json(value: Any) -> str | None:
        return None if value is None else json.dumps(value)

    @staticmethod
    def from_json(value: str | None) -> Any:
        return None if value is None else json.loads(value)

    def ensure_ready(self) -> None:
        try:
            self.initialize()
        except sqlite3.Error as exc:
            raise PersistenceError(f"database initialization failed: {exc}") from exc
