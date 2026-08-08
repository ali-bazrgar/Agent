# Database Architecture

## Storage strategy

The system uses multiple storage technologies, each with a clear role. No single storage technology is responsible for every data type.

## Storage domains

- Relational storage: authoritative structured state
- File/object storage: immutable source documents and extracted artifacts
- Vector index: derived embeddings
- Lexical index: derived full-text index
- Cache: disposable performance data
- Optional graph tables: relationship data, not a dedicated graph database in v1

## Relational storage

The relational database is the source of truth for structured application state. The initial backend is SQLite for local-first development, but repository interfaces must be backend-agnostic so PostgreSQL can be introduced later without rewriting domain logic.

Representative entities:

- users
- sessions
- messages
- documents
- chunks
- sources
- memories
- personal_knowledge_entries
- entities
- facts
- relationships
- flashcards
- reviews
- learning_states
- executions
- tool_calls
- research_runs

## File and object storage

Original source files and immutable blobs are stored outside the relational core. The database stores metadata and references to them.

## Derived indexes

Vector and lexical indexes are derived indexes. They must be rebuildable from authoritative relational records and source files.

## Repository boundaries

The domain/application layer depends on repository interfaces, not on SQLite directly. Concrete repositories may use SQLite in the initial implementation.

## Deletion and consistency

Deletion must propagate through related derived data. The architecture must avoid orphaned embeddings, chunks, facts, or flashcards after a document or memory is removed.

## Migrations and schema evolution

Schema changes should follow a migration workflow. Production data must not be mutated manually.
