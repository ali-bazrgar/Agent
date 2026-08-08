from __future__ import annotations

PHASE11_MEMORY_MIGRATION: tuple[str, ...] = (
    "ALTER TABLE memory_records ADD COLUMN structured_data_json TEXT NOT NULL DEFAULT '{}'",
    "ALTER TABLE memory_records ADD COLUMN classification TEXT NOT NULL DEFAULT 'explicit'",
    "ALTER TABLE memory_records ADD COLUMN last_accessed_at TEXT",
    "ALTER TABLE memory_records ADD COLUMN access_count INTEGER NOT NULL DEFAULT 0",
)
