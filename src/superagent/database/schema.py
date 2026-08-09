from __future__ import annotations

from collections.abc import Iterable

INITIAL_SCHEMA_STATEMENTS: tuple[str, ...] = (
    """
    CREATE TABLE IF NOT EXISTS schema_migrations (version TEXT PRIMARY KEY, applied_at TEXT NOT NULL)
    """,
    """
    CREATE TABLE IF NOT EXISTS documents (id TEXT PRIMARY KEY, title TEXT NOT NULL, source_type TEXT NOT NULL, source_uri TEXT, content_hash TEXT, metadata_json TEXT, created_at TEXT NOT NULL, updated_at TEXT NOT NULL)
    """,
    """
    CREATE TABLE IF NOT EXISTS document_chunks (id TEXT PRIMARY KEY, document_id TEXT NOT NULL, content TEXT NOT NULL, chunk_index INTEGER NOT NULL, token_count INTEGER, metadata_json TEXT, created_at TEXT NOT NULL)
    """,
    """
    CREATE TABLE IF NOT EXISTS memory_records (id TEXT PRIMARY KEY, kind TEXT NOT NULL, content TEXT NOT NULL, confidence REAL NOT NULL, importance REAL NOT NULL, relevance REAL NOT NULL, status TEXT NOT NULL, source_type TEXT NOT NULL, source_uri TEXT, provenance TEXT, valid_from TEXT, valid_until TEXT, created_at TEXT NOT NULL, updated_at TEXT NOT NULL)
    """,
    """
    CREATE TABLE IF NOT EXISTS executions (id TEXT PRIMARY KEY, request_id TEXT, status TEXT NOT NULL, model_calls INTEGER NOT NULL DEFAULT 0, tool_calls INTEGER NOT NULL DEFAULT 0, retries INTEGER NOT NULL DEFAULT 0, created_at TEXT NOT NULL, completed_at TEXT, metadata_json TEXT)
    """,
    """
    CREATE TABLE IF NOT EXISTS flashcards (id TEXT PRIMARY KEY, front TEXT NOT NULL, back TEXT NOT NULL, source_type TEXT, source_uri TEXT, difficulty REAL NOT NULL, created_at TEXT NOT NULL, updated_at TEXT NOT NULL)
    """,
    """
    CREATE TABLE IF NOT EXISTS reviews (id TEXT PRIMARY KEY, flashcard_id TEXT NOT NULL, reviewed_at TEXT NOT NULL, outcome TEXT NOT NULL, interval_days INTEGER, ease_factor REAL)
    """,
)

PHASE3_MIGRATION_STATEMENTS: tuple[str, ...] = (
    """
    CREATE TABLE IF NOT EXISTS sources (source_id TEXT PRIMARY KEY, source_type TEXT NOT NULL, uri TEXT, locator TEXT, title TEXT, content_hash TEXT, metadata_json TEXT, provenance_json TEXT, created_at TEXT NOT NULL, updated_at TEXT NOT NULL, UNIQUE(content_hash))
    """,
    """
    CREATE TABLE IF NOT EXISTS knowledge_documents (document_id TEXT PRIMARY KEY, source_id TEXT NOT NULL, title TEXT NOT NULL, document_type TEXT NOT NULL DEFAULT 'document', content_type TEXT, content_hash TEXT, status TEXT NOT NULL DEFAULT 'active', version INTEGER NOT NULL DEFAULT 1, blob_uri TEXT, metadata_json TEXT, created_at TEXT NOT NULL, updated_at TEXT NOT NULL, FOREIGN KEY(source_id) REFERENCES sources(source_id) ON DELETE RESTRICT)
    """,
    """
    CREATE TABLE IF NOT EXISTS document_versions (version_id TEXT PRIMARY KEY, document_id TEXT NOT NULL, title TEXT, content TEXT, content_hash TEXT, content_type TEXT, status TEXT NOT NULL DEFAULT 'active', metadata_json TEXT, created_at TEXT NOT NULL, updated_at TEXT NOT NULL, FOREIGN KEY(document_id) REFERENCES knowledge_documents(document_id) ON DELETE RESTRICT)
    """,
    """
    CREATE TABLE IF NOT EXISTS knowledge_chunks (chunk_id TEXT PRIMARY KEY, document_id TEXT NOT NULL, version_id TEXT, content TEXT NOT NULL, content_hash TEXT, chunk_index INTEGER NOT NULL, token_count INTEGER, character_count INTEGER, language TEXT, metadata_json TEXT, created_at TEXT NOT NULL, FOREIGN KEY(document_id) REFERENCES knowledge_documents(document_id) ON DELETE RESTRICT, FOREIGN KEY(version_id) REFERENCES document_versions(version_id) ON DELETE SET NULL)
    """,
    """
    CREATE TABLE IF NOT EXISTS embedding_records (embedding_id TEXT PRIMARY KEY, chunk_id TEXT, document_id TEXT, version_id TEXT, model_id TEXT NOT NULL, dimension INTEGER NOT NULL, vector_json TEXT NOT NULL, content_hash TEXT, metadata_json TEXT, created_at TEXT NOT NULL, updated_at TEXT NOT NULL, FOREIGN KEY(chunk_id) REFERENCES knowledge_chunks(chunk_id) ON DELETE RESTRICT, FOREIGN KEY(document_id) REFERENCES knowledge_documents(document_id) ON DELETE RESTRICT, FOREIGN KEY(version_id) REFERENCES document_versions(version_id) ON DELETE SET NULL)
    """,
    """
    CREATE TABLE IF NOT EXISTS knowledge_items (knowledge_id TEXT PRIMARY KEY, kind TEXT NOT NULL, title TEXT, content TEXT, content_hash TEXT, source_id TEXT, document_id TEXT, version_id TEXT, chunk_id TEXT, metadata_json TEXT, provenance_json TEXT, created_at TEXT NOT NULL, updated_at TEXT NOT NULL, FOREIGN KEY(source_id) REFERENCES sources(source_id) ON DELETE RESTRICT, FOREIGN KEY(document_id) REFERENCES knowledge_documents(document_id) ON DELETE RESTRICT, FOREIGN KEY(version_id) REFERENCES document_versions(version_id) ON DELETE SET NULL, FOREIGN KEY(chunk_id) REFERENCES knowledge_chunks(chunk_id) ON DELETE SET NULL)
    """,
    "CREATE TABLE IF NOT EXISTS tags (tag_id TEXT PRIMARY KEY, resource_type TEXT NOT NULL, resource_id TEXT NOT NULL, name TEXT NOT NULL, value TEXT, created_at TEXT NOT NULL)",
    "CREATE TABLE IF NOT EXISTS vector_index_entries (entry_id TEXT PRIMARY KEY, model_id TEXT NOT NULL, dimension INTEGER NOT NULL, vector_json TEXT NOT NULL, metadata_json TEXT, created_at TEXT NOT NULL, updated_at TEXT NOT NULL)",
    "CREATE TABLE IF NOT EXISTS lexical_index_entries (entry_id TEXT PRIMARY KEY, chunk_id TEXT NOT NULL, content TEXT NOT NULL, created_at TEXT NOT NULL, FOREIGN KEY(chunk_id) REFERENCES knowledge_chunks(chunk_id) ON DELETE RESTRICT)",
    "CREATE VIRTUAL TABLE IF NOT EXISTS chunk_search_fts USING fts5(chunk_id UNINDEXED, content)",
)

PHASE10_MIGRATION_STATEMENTS: tuple[str, ...] = (
    "CREATE TABLE IF NOT EXISTS learning_states (flashcard_id TEXT PRIMARY KEY, state TEXT NOT NULL DEFAULT 'new', due_date TEXT NOT NULL, interval_days INTEGER NOT NULL DEFAULT 0, repetition INTEGER NOT NULL DEFAULT 0, ease_factor REAL NOT NULL DEFAULT 2.5, stability REAL NOT NULL DEFAULT 1.0, difficulty REAL NOT NULL DEFAULT 0.3, last_reviewed_at TEXT, created_at TEXT NOT NULL, updated_at TEXT NOT NULL, FOREIGN KEY(flashcard_id) REFERENCES flashcards(id) ON DELETE CASCADE)",
    "CREATE TABLE IF NOT EXISTS knowledge_relationships (relationship_id TEXT PRIMARY KEY, source_id TEXT NOT NULL, target_id TEXT NOT NULL, relation_type TEXT NOT NULL, metadata_json TEXT, created_at TEXT NOT NULL)",
)

MEMORY_SCOPE_MIGRATION_STATEMENTS: tuple[str, ...] = (
    "ALTER TABLE memory_records ADD COLUMN scope_type TEXT NOT NULL DEFAULT 'user'",
    "ALTER TABLE memory_records ADD COLUMN owner_id TEXT",
    "ALTER TABLE memory_records ADD COLUMN conversation_id TEXT",
    "ALTER TABLE memory_records ADD COLUMN project_id TEXT",
    "CREATE INDEX IF NOT EXISTS idx_memory_scope_owner ON memory_records(owner_id, scope_type)",
    "CREATE INDEX IF NOT EXISTS idx_memory_scope_conversation ON memory_records(owner_id, conversation_id)",
)

def get_schema_statements() -> Iterable[str]:
    return INITIAL_SCHEMA_STATEMENTS

def get_migration_statements() -> dict[str, tuple[str, ...]]:
    return {
        "001_initial_schema": INITIAL_SCHEMA_STATEMENTS,
        "002_phase3_persistence": PHASE3_MIGRATION_STATEMENTS,
        "003_phase10_learning": PHASE10_MIGRATION_STATEMENTS,
        "004_memory_scopes": MEMORY_SCOPE_MIGRATION_STATEMENTS,
    }
