# SuperAgent — Implementation Overview

This repository contains the implemented SuperAgent platform through the current production-hardening and UI integration pass.

## Implemented capabilities

- **Foundation:** typed configuration, provider contracts, application composition root, SQLite persistence, migrations, and dependency injection.
- **Knowledge ingestion:** source/document/version/chunk persistence, content hashing, embeddings, provenance, duplicate detection, and retrieval-ready indexes.
- **RAG:** dense retrieval, lexical FTS5 retrieval, reciprocal-rank fusion, hybrid retrieval, filtering, and reranking.
- **Context engine:** token estimation, deterministic budgeting, deduplication, evidence ranking, prompt construction, and provenance.
- **Agent runtime:** routing, planning, orchestration, criticism, verification, revision, execution state, tool execution, and end-to-end error handling.
- **Memory:** explicit/inferred memory extraction, ranking, lifecycle, consolidation, durable persistence, access tracking, and soft deletion.
- **Tools and research:** calculator, time, web search, SSRF-protected web fetch, research pipeline, registry, executor, risk levels, and execution limits. Configured web research is now wired from application settings into the tool registry.
- **Learning:** flashcard extraction, knowledge relationships, FSRS-6 scheduling, review submission, due-review queue, learning statistics, and durable learning state.
- **API:** canonical `/v1/*` routes plus `/api/v1/*` compatibility routes, including chat, executions, documents, memories, learning, tools, and health.
- **Web UI:** Chat, Dashboard, Data Center, Knowledge Graph, Learning Center, Execution Center, Settings Center, and API documentation views, with frontend calls aligned to the FastAPI contracts.
- **Production hardening:** structured logging, provider health checks, retry/error classification, security limits, Windows/Linux CI, strict-warning Python tests, frontend typecheck/build, and production dependency auditing.

## Important runtime contract

The application is a client of OpenAI-compatible local model servers. The default provider bases are:

- LLM: `http://127.0.0.1:8080`
- Embedding: `http://127.0.0.1:8081`
- Reranker: `http://127.0.0.1:8082`

The provider itself appends the OpenAI-compatible paths such as `/v1/chat/completions`, `/v1/embeddings`, and `/v1/rerank`. The SuperAgent backend's own compatibility prefix `/api/v1` is a separate API concern and must not be added to the llama.cpp provider base URLs.

## Verification gates

The repository is expected to satisfy all of these before a change is considered complete:

```bash
python -m pytest -q -W error
npm run typecheck
npm run build
```

GitHub Actions additionally runs the Python suite on Linux and Windows and performs a production dependency audit for the frontend.

## Documentation source of truth

The `docs/` directory contains architecture specifications, security and deployment requirements, testing strategy, and implementation status. When behavior changes, the corresponding specification and this overview must be updated in the same change.
