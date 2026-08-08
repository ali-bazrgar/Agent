# Implementation Roadmap

## Architecture phase status

The repository is currently in the architecture phase. No production application code, database migrations, or provider implementations should be created yet.

## Phase 0 — Architecture completion

Deliver:

- final architecture documents
- ADRs for storage, provider abstraction, memory, context, and orchestration
- clear module boundaries
- repository interfaces
- configuration conventions
- testing strategy

Acceptance:

The architecture is implementation-ready and does not depend on a specific runtime, database, vector engine, or context size.

## Phase 1 — Foundation

Implement:

- Python packaging and dependency structure
- configuration and environment management
- logging and error handling
- base domain models
- repository interfaces
- provider interfaces
- test scaffolding

Acceptance:

The foundation supports future implementation without coupling to specific infrastructure.

## Phase 2 — Runtime adapters

Implement:

- LLM provider adapter
- embedding provider adapter
- reranker provider adapter
- health checks and runtime capability detection

Acceptance:

The application can talk to local or remote model providers through the provider interfaces.

## Phase 3 — Persistence

Implement:

- relational schema
- repository implementations
- file/blob storage handling
- vector and lexical index scaffolding

Acceptance:

Structured state and source documents survive restarts and can be queried through repositories.

## Phase 4 — Ingestion and retrieval

Implement:

- ingestion pipeline
- parsing and chunking
- embedding and indexing
- hybrid retrieval
- reranking

Acceptance:

A document can be ingested, indexed, retrieved, and attributed.

## Phase 5 — Context and memory

Implement:

- dynamic context engine
- memory lifecycle
- explicit/inferred memory handling
- PKM storage

Acceptance:

The system can build context budgets and retrieve relevant memories without overloading the model window.

## Phase 6 — Agent and learning

Implement:

- adaptive orchestration
- tool execution
- learning engine
- FSRS scheduler abstraction

Acceptance:

Simple requests stay cheap while complex requests can use a deeper execution path.

## Phase 7 — API and evaluation

Implement:

- versioned API
- observability
- evaluation harness
- security controls

Acceptance:

External clients can access the backend through stable contracts while the system remains measurable and auditable.
