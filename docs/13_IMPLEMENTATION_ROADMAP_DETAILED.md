# Implementation Roadmap — Detailed Historical Plan

> **Status:** historical planning document. The repository has progressed beyond the Phase 0–4 scope described below. Current behavior is documented by the architecture specifications and `IMPLEMENTATION_OVERVIEW.md`.

This document records the original incremental delivery plan. It remains useful for understanding why the codebase is divided into provider, persistence, retrieval, context, orchestration, memory, tool, learning, and UI boundaries.

## Original acceptance model

Every sprint was intended to deliver code, automated tests, and synchronized documentation. Real model servers were deliberately kept out of the default unit-test path; provider adapters are tested through contracts and controlled HTTP behavior.

## Historical phases

### Phase 0 — Architecture

- Typed configuration and `.env.example`.
- Provider protocols for LLM, embeddings, reranking, and web research.
- SQLite schema and migration skeleton.
- ADRs for storage, provider abstraction, memory, context, and orchestration.

### Phase 1 — Foundation

- FastAPI application factory.
- Typed settings and environment loading.
- Provider contracts and mockable boundaries.
- SQLite repositories and migration infrastructure.
- Health endpoint and foundational tests.

### Phase 2 — Model runtime

- llama.cpp HTTP adapters for LLM, embedding, and reranking.
- Provider health diagnostics, timeouts, retries, and error classification.
- Runtime tests without requiring GGUF models in CI.

### Phase 3 — Persistence and ingestion

- Durable documents, versions, chunks, sources, embeddings, knowledge items, and tags.
- Content hashing and duplicate detection.
- Canonical ingestion pipeline used by the document API.

### Phase 4 — Retrieval

- Dense and lexical retrieval.
- Hybrid retrieval and reciprocal-rank fusion.
- Reranking and provenance-aware evidence selection.

## Current delivery model

Later phases are now maintained by their dedicated specifications:

- Context engine: `docs/14_CONTEXT_ENGINE_SPECIFICATION.md`
- Agent orchestration: `docs/15_AGENT_ORCHESTRATION_SPECIFICATION.md`
- Memory lifecycle: `docs/16_MEMORY_LIFECYCLE_SPECIFICATION.md`
- Tool system: `docs/17_TOOL_SYSTEM_SPECIFICATION.md`
- Web research: `docs/18_WEB_RESEARCH_SPECIFICATION.md`
- End-to-end runtime: `docs/19_END_TO_END_RUNTIME_SPECIFICATION.md`
- Production runtime: `docs/20_PRODUCTION_RUNTIME_SPECIFICATION.md`
- Learning engine: `docs/24_LEARNING_ENGINE_SPECIFICATION.md`
- UI/UX: `docs/25_UI_UX_SPECIFICATION.md`
- Deployment: `docs/26_DEPLOYMENT_SPECIFICATION.md`

## Current quality gates

A change is not considered complete until the repository passes:

```bash
python -m pytest -q -W error
npm run typecheck
npm run build
```

The GitHub Actions matrix must also pass on both Linux and Windows for the Python suite, plus the frontend dependency audit.