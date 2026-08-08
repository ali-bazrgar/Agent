# System Architecture — Implementation-Ready Plan

This document takes the high-level system architecture and turns it into an implementation-ready plan for Phase 0 → Phase 1. It focuses on concrete developer-facing artifacts: repository layout, interface contracts (Protocols), wiring points, runtime configuration, and next-step deliverables.

## 1. Goals

- Keep a modular monolith with strict boundaries between domain and infrastructure.
- Provide stable Protocols (Python typing.Protocol) for external providers (LLM, Embedding, Reranker, VectorStore).
- Make runtime pluggable via environment configuration.
- Keep code Windows-friendly (pathlib.Path, no hardcoded absolute paths).

## 2. Recommended repository layout

D:/SuperAgent

- src/superagent/
  - api/
    - routes/
    - models.py        # Pydantic request/response models
    - app.py           # FastAPI app factory
  - core/
    - domain_models.py
    - use_cases.py
  - agents/
    - router.py
    - planner.py
    - orchestrator.py
    - state.py
  - memory/
    - models.py
    - store.py         # memory store API (wraps repositories)
    - consolidation.py
  - knowledge/
    - ingest/
      - parsers.py
      - normalizers.py
      - chunker.py
    - models.py
  - retrieval/
    - retrievers.py
    - fusion.py
    - rerank_orchestrator.py
  - embeddings/
    - interfaces.py
    - cache.py
  - reranker/
    - interfaces.py
    - adapter.py
  - llm/
    - interfaces.py
    - llama_adapter.py
  - learning/
    - flashcards.py
    - fsrs_scheduler.py
  - tools/
    - tool_registry.py
    - tool_adapters.py
  - db/
    - repositories.py
    - migrations/
  - storage/
    - file_store.py
  - config/
    - settings.py
  - observability/
    - tracing.py
    - metrics.py
  - tests/
    - unit/
    - integration/

Rationale: each package is small and testable. Domain code in core/ never imports infrastructure; it depends only on well-defined Protocols.

## 3. Provider Protocol sketches

Place Protocols in dedicated small modules (e.g., llm/interfaces.py). Keep them minimal and typed.

Example (sketch):

- llm/interfaces.py

```python
from typing import Protocol, List, Optional
from pydantic import BaseModel

class ModelHealth(BaseModel):
    name: str
    max_context_tokens: int
    supports_streaming: bool

class LLMResponse(BaseModel):
    text: str
    tokens_used: int

class LLMProvider(Protocol):
    async def generate(self, prompt: str, *, max_tokens: int, stop: Optional[List[str]] = None) -> LLMResponse: ...
    async def stream(self, prompt: str, *, max_tokens: int) -> "AsyncIterator[str]": ...
    async def health(self) -> ModelHealth: ...
```

- embeddings/interfaces.py

```python
class EmbeddingProvider(Protocol):
    async def embed(self, texts: list[str]) -> list[list[float]]: ...
    async def batch_embed(self, texts: list[list[str]]) -> list[list[list[float]]]: ...
    async def health(self) -> dict: ...
```

- reranker/interfaces.py

```python
class RerankerProvider(Protocol):
    async def score(self, query: str, candidates: list[str]) -> list[float]: ...
```

Adapters implement these and are constructed at startup by reading configuration.

## 4. Wiring and dependency injection

- Application startup (api/app.py) reads typed settings (pydantic BaseSettings) and constructs concrete implementations of providers and repositories.
- Use small DI helpers (factory functions) rather than heavy frameworks.
- Provide an AppState object to FastAPI for access to provider instances.

## 5. Context Engine contract

Context Engine receives:
- system_instructions: str
- user_request: str
- memory_candidates: list[MemoryRecord]
- knowledge_candidates: list[ChunkRecord]
- token_budget: int

Responsibilities:
- Score and select items under token budget
- Compress (summarize/extract) items to reduce tokens while preserving provenance
- Return final prompt payload and a trace of selected IDs and scores for observability

## 6. Observability and tracing

Design execution traces to include:
- execution_id, session_id, user_id
- selected evidence ids (chunks/memories) with scores
- model calls with token counts and latencies
- reranker/hit lists
- tool calls and outcomes

Store traces in relational DB and optionally expose /executions/{id} for debugging.

## 7. Failure boundaries

- Adapter-level try/except with explicit fallback: e.g., reranker failure → use original scores; embedding failure during ingestion → mark pending and preserve source.
- No optional subsystem crash should corrupt persistent data.

## 8. Next steps (Phase 0 → Phase 1)

1. Implement typed settings and AppState wiring.
2. Define Protocols for LLM/Embedding/Reranker and provide trivial sync async mock implementations for tests.
3. Add repository interfaces and a minimal sqlite schema (see docs/10_DATABASE_SCHEMA_IMPLEMENTATION.md).
4. Add a health endpoint that checks all configured providers.
5. Add tests for core wiring (mock providers) and a smoke test for startup.


---

See also: [00_PROJECT_VISION.md](D:/SuperAgent/docs/00_PROJECT_VISION.md) and [03_AGENT_ARCHITECTURE.md](D:/SuperAgent/docs/03_AGENT_ARCHITECTURE.md).
