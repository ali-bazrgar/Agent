from __future__ import annotations

import sqlite3

from superagent.database.config import DatabaseConfig
from superagent.database.engine import DatabaseEngine


def test_schema_migration_creates_all_phase3_tables(tmp_path) -> None:
    db_file = tmp_path / "test_migration.db"
    config = DatabaseConfig(path=db_file)
    engine = DatabaseEngine(config)

    # Initial initialize
    engine.ensure_ready()

    # Re-running initialize must be idempotent and succeed without error
    engine.initialize()
    engine.initialize()

    with engine.connect() as connection:
        cursor = connection.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = {row[0] for row in cursor.fetchall()}

    expected_tables = {
        "sources",
        "document_versions",
        "embedding_records",
        "knowledge_items",
        "knowledge_chunks",
        "tags",
        "schema_migrations",
    }
    for table in expected_tables:
        assert table in tables, f"Table {table} missing from SQLite schema"

    with engine.connect() as connection:
        cursor = connection.execute("SELECT version FROM schema_migrations")
        versions = {row[0] for row in cursor.fetchall()}

    assert "001_initial_schema" in versions
    assert "002_phase3_persistence" in versions
