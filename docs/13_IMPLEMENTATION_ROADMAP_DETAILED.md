# Implementation Roadmap — Detailed (Phase 0 → Phase 2)

This roadmap expands the existing high-level roadmap into concrete, actionable sprints and acceptance criteria for the first phases. The goal is to get a testable, pluggable foundation without adding heavy external dependencies.

Conventions
- Sprint length: 1 week (adjust to team cadence)
- Deliverables are code, tests, and documentation updates.
- Acceptance requires automated tests and a short demo script that verifies behavior.

Phase 0 — Architecture (deliverable)
- Deliver:
  - Typed configuration (pydantic BaseSettings) and .env.example
  - Repository layout (packages and __init__ files)
  - Provider Protocols for LLM, Embedding, Reranker
  - Concrete DB schema drafts and migration skeleton
  - ADRs for major decisions (model runtime, vector strategy, storage)
- Acceptance:
  - PR with docs and file layout approved
  - tests/ placeholder with basic CI check (import everything)

Sprint 1 — Foundation (Phase 1 core)
- Implement:
  - pyproject.toml with minimal dependencies (FastAPI, pydantic, sqlite)
  - src/superagent/config/settings.py with typed settings and env loader
  - App factory src/superagent/api/app.py that creates an AppState and registers a health route
  - Provider Protocols in src/superagent/llm/interfaces.py, embeddings/interfaces.py, reranker/interfaces.py
  - Mock providers for testing
  - DB migration skeleton (migrations/)
- Tests:
  - unit test verifying app startup constructs AppState with mock providers
  - integration smoke test connecting to sqlite in-memory DB
- Acceptance criteria:
  - `pytest` runs foundation tests successfully
  - `/health` returns basic provider statuses using mock providers

Sprint 2 — Model Runtime Adapters (Phase 2 core)
- Implement:
  - llama.cpp HTTP adapter (llm/llama_adapter.py) that implements LLMProvider but does not start server
  - Embedding adapter that wraps configured EMBEDDING_BASE_URL
  - Reranker adapter stub
  - Provider health endpoints to check remote endpoints
- Tests:
  - unit tests for adapters using HTTP mocking (responses or httpx mocking)
- Acceptance:
  - startup with configured dummy endpoints does not crash
  - health shows unreachable/ok statuses

Sprint 3 — Persistence & Repositories (Phase 3 core)
- Implement:
  - db/repositories.py with repository classes for Users, Documents, Chunks, Memories
  - migration scripts to create base tables (from docs/10_DATABASE_SCHEMA_IMPLEMENTATION.md)
  - a simple repository test harness
- Tests:
  - repository unit tests using sqlite in-memory and transactional rollbacks
- Acceptance:
  - data persists across restart in local sqlite test (file-based)

Sprint 4 — Ingestion plumbing (Phase 4 initial)
- Implement:
  - minimal ingestion pipeline that accepts a text or markdown file, chunks it, computes content hashes, stores document+chunks, and enqueues embedding tasks
  - embedding queue simplified to synchronous for Phase 1
- Tests:
  - ingest small document and assert chunks created, content_hash matches, embedding row created or marked pending
- Acceptance:
  - Document ingestion round-trip works in CI with mocked embedding provider

Cross-cutting tasks (ongoing)
- Observability: implement Execution trace model and persistence; wire traces at important transitions.
- Tests: implement mock providers and unit tests such that real GGUF models not required for most CI runs.
- Security: input validation, file path protections, SSRF protections on web requests.

Minimum artifacts to ship after Phase 1
- src/superagent/config/settings.py
- src/superagent/llm/interfaces.py, embeddings/interfaces.py, reranker/interfaces.py
- src/superagent/api/app.py with /health endpoint
- migrations/ skeleton with base create tables
- docs/* updated: architecture, DB schema, roadmap (this change)
- tests/ foundation tests

Acceptance criteria for Phase 1
- `pytest` passes unit and integration tests using mock providers and sqlite in-memory
- `python -m superagent.api.app` (or uvicorn invocation) starts the FastAPI app and responds to /health
- Basic ingestion test (mocked embed) passes

Operational notes and trade-offs
- Keep real-model tests out of CI by marking them with pytest markers (e.g., @pytest.mark.integration or @pytest.mark.real_model).
- Prefer simplicity for Phase 1: synchronous flows for ingestion and embedding jobs; refactor to background workers when required.
- Persist only necessary runtime state in DB; ephemeral working memory can stay in-process until more complex needs arise.

Next review
- After completing Sprint 2, review token-budgeting requirements and Context Engine interfaces (decide exact prompt format and trace schema).