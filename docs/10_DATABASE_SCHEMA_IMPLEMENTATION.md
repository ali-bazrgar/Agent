# Database Schema — Implementation Proposal

This document proposes concrete relational schemas for the core application objects. These SQL definitions are intended as a starting point for migrations (use a migration tool such as Alembic or sqlmodel's migration strategy). Use timezone-aware timestamps (UTC) and stable UUID primary keys.

Design notes
- Keep vector embeddings and indexes as derived artifacts referenced by relational rows; do not store raw embedding vectors as blobs in transactional tables unless necessary (store reference to vector store id).
- Use content hashing to deduplicate document/chunk ingestion.
- Keep original source files in storage and reference them with file_id.

Example SQL (SQLite-compatible; adjust types for Postgres if later needed)

-- users
CREATE TABLE IF NOT EXISTS users (
    id TEXT PRIMARY KEY, -- uuid
    username TEXT UNIQUE,
    created_at TEXT NOT NULL,
    updated_at TEXT
);

-- sessions
CREATE TABLE IF NOT EXISTS sessions (
    id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL,
    created_at TEXT NOT NULL,
    last_active_at TEXT,
    FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
);

-- documents (source of truth)
CREATE TABLE IF NOT EXISTS documents (
    id TEXT PRIMARY KEY,
    user_id TEXT,
    title TEXT,
    source_type TEXT,
    source_uri TEXT,
    file_id TEXT, -- pointer to storage blob
    content_hash TEXT NOT NULL,
    created_at TEXT NOT NULL,
    updated_at TEXT,
    FOREIGN KEY(user_id) REFERENCES users(id)
);

-- chunks (derived)
CREATE TABLE IF NOT EXISTS chunks (
    id TEXT PRIMARY KEY,
    document_id TEXT NOT NULL,
    chunk_index INTEGER NOT NULL,
    text TEXT NOT NULL,
    token_count INTEGER,
    chunk_hash TEXT NOT NULL,
    metadata JSON,
    created_at TEXT NOT NULL,
    FOREIGN KEY(document_id) REFERENCES documents(id) ON DELETE CASCADE
);

-- embeddings (metadata pointing at vector store)
CREATE TABLE IF NOT EXISTS embeddings (
    id TEXT PRIMARY KEY,
    chunk_id TEXT NOT NULL,
    vector_id TEXT NOT NULL, -- id in the vector backend
    dimension INTEGER,
    created_at TEXT NOT NULL,
    FOREIGN KEY(chunk_id) REFERENCES chunks(id) ON DELETE CASCADE
);

-- memories
CREATE TABLE IF NOT EXISTS memories (
    id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL,
    type TEXT NOT NULL,
    content TEXT NOT NULL,
    structured JSON,
    source TEXT,
    provenance JSON,
    confidence REAL,
    importance REAL,
    valid_from TEXT,
    valid_until TEXT,
    last_accessed_at TEXT,
    access_count INTEGER DEFAULT 0,
    created_at TEXT NOT NULL,
    updated_at TEXT,
    FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
);

-- flashcards
CREATE TABLE IF NOT EXISTS flashcards (
    id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL,
    source_document_id TEXT,
    source_chunk_id TEXT,
    question TEXT NOT NULL,
    answer TEXT NOT NULL,
    fsrs_state JSON,
    created_at TEXT NOT NULL,
    updated_at TEXT,
    FOREIGN KEY(user_id) REFERENCES users(id)
);

-- executions / traces
CREATE TABLE IF NOT EXISTS executions (
    id TEXT PRIMARY KEY,
    user_id TEXT,
    session_id TEXT,
    request_type TEXT,
    start_time TEXT NOT NULL,
    end_time TEXT,
    status TEXT,
    model_calls JSON,       -- model call metadata: model_name, tokens_in, tokens_out, latency
    evidence JSON,         -- list of selected evidence ids with scores
    tool_calls JSON,
    notes TEXT
);

-- model_providers
CREATE TABLE IF NOT EXISTS model_providers (
    id TEXT PRIMARY KEY,
    provider_type TEXT,
    base_url TEXT,
    metadata JSON,
    last_health_check TEXT
);

Indexes and considerations
- Index chunks.content_hash, documents.content_hash for fast deduplication checks.
- Index embeddings.chunk_id and embeddings.vector_id for cleanup operations.
- Use partial indexing or TTL for ephemeral working-memory records if stored in DB.

Migration and evolution
- Use a migration framework (Alembic or similar) and keep migrations in migrations/
- Do not change column semantics silently; provide migration scripts for evolving schemas.

Vector store integration
- Keep vector store as separate service/backing store. Store only vector_id references and dimension metadata in embeddings table.
- Provide a cleanup job that reconciles relational deletions with vector store removals.

Backups
- Document regular backup strategy for database and storage path. For local-first, default to local daily snapshots and a user-initiated export/import flow.

Security
- Ensure file references do not allow path traversal; storage layer must validate file IDs and paths.

This schema is intended as a starting point for implementation. Adjust and extend it during Phase 1 based on concrete repository and storage choices.
