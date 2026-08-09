# SuperAgent — Project State

This repository is the canonical implementation of the SuperAgent runtime. The backend and a temporary schematic/test frontend are developed in parallel. The final production UI will be redesigned after the backend gates are complete.

## Current baseline

- `main` is the canonical integration branch.
- The backend contains model/provider capability resolution, context budgeting, hybrid retrieval, reranking, persistent memory lifecycle components, learning components, execution budgets, model-selected tool execution, critic/verifier/revision stages, and SQLite persistence.
- The current frontend is intentionally a functional integration-test surface, not the final product UI.

## Important architectural decisions

The default agentic path is **model-driven** for semantic actions. Natural-language keyword matching must not decide whether a user asked to save memory, search knowledge, browse the web, calculate something, or use another tool. The LLM receives the available tool schemas and may select zero or more tools. Deterministic routing remains only as an explicit compatibility mode.

Persistent memory **recall** is different from semantic memory writes. Every user turn performs a bounded, relevance-ranked lookup against persistent memory before context construction by default. This gives a small-context model access to durable user facts without replaying the full conversation. The LLM still decides whether to create, update, consolidate, or delete memories through the memory tool/lifecycle path.

The target architecture is a fixed user-selected runtime context (for example 8K, 32K, or 128K) combined with retrieval-backed effective memory. The context is not allowed to grow monotonically with the conversation. The database is the long-term memory; the LLM context is a temporary working set containing only relevant evidence.

## Comprehensive audit — current findings

### Confirmed and fixed

- **Obsolete frontend fork removed:** the old `react_ui_backup/` application contained a second React/Express implementation with seeded in-memory data and stale routes such as `/api/v1/flashcards`. It was not part of the active build and could create architectural ambiguity, so the entire unused backup tree was removed.
- **Document domain/repository mismatch fixed:** `Document` now explicitly owns its persisted `chunks`, and SQLite document hydration reconstructs the real `Source`, document metadata, version information and knowledge chunks instead of returning an incomplete object. This also makes the knowledge-graph endpoint operate on actual persisted chunk relationships.
- **Document deletion hardened:** deletion now cleans both current knowledge chunks and legacy `document_chunks`, embeddings, lexical/FTS indexes, knowledge items, tags, relationships, versions and document rows before removing an unreferenced source.
- **Silent chunk-index failures removed:** `SqliteChunkRepository` previously swallowed exceptions while writing `knowledge_chunks`, FTS and lexical indexes. Those failures could make ingestion appear successful while retrieval data was incomplete. Index persistence is now transactional and errors propagate as `PersistenceError`.
- **Capability reporting made conservative:** the llama.cpp adapter no longer claims vision/audio/video support merely because the HTTP endpoint exists. Those capabilities must come from verified model metadata/profile configuration.
- **Hidden generation fallback removed:** capability-to-runtime resolution no longer introduces a default 1024-token output cap when no model/provider limit exists.
- **Runtime validation strengthened:** runtime configuration rejects an output limit or explicit output reservation larger than the selected context window, and updating runtime configuration also updates the already-created agentic provider wrapper.
- **Tool catalog consistency fixed:** `/v1/tools` now uses the same application container/registry as the active chat path rather than constructing a separate container with potentially different runtime state.
- **Schematic API playground corrected:** frontend API test routes now match the canonical `/api/v1/learning/...` learning routes and expose the active configuration, tools and knowledge-graph endpoints. HTTP status is no longer hard-coded as `200`.
- **Legacy migration hardening:** the memory lifecycle `ALTER TABLE` migration is now idempotent for partially upgraded SQLite databases, avoiding failures when one or more columns already exist.

### Findings deliberately retained

- The deterministic router and heuristic memory extractor remain in the repository as **explicit compatibility/legacy modes**. They are not the default semantic decision mechanism. Removing them now would break compatibility tests and would not improve the normal model-driven path.
- The current schematic frontend remains intentionally functional and is being used to test backend contracts. It will not be treated as the final UI architecture.

### Still open and high priority

- Orchestrator/agentic-level streaming is not complete yet. Provider streaming must feed the full tool → critic → verifier → revision → memory lifecycle without bypassing execution budgets.
- Token accounting still needs a normalized prompt/output/tool/critic/verifier breakdown rather than relying mainly on a single aggregate integer.
- Chat telemetry and proxy failure behavior need focused regression tests.
- Browser/API runtime behavior still needs a real local test with correlated request IDs.
- File ingestion still needs first-class safe type detection, size limits, extraction, provenance, hashing/deduplication and asynchronous status.
- Knowledge-file and memory-file ingestion should become separate explicit workflows over shared safe file primitives.
- Model management needs stronger capability discovery, validation, health, identity and safe runtime override behavior.
- End-to-end integration coverage must prove `Generation -> Tool Selection -> Tool Execution -> Critic -> Verification -> Revision -> Memory` with real provider-like responses.
- Persistence, concurrency, cancellation, idempotency, error mapping and observability need another hardening pass.

## Runtime and model controls

- One effective LLM runtime configuration is resolved at the application composition root and injected into the provider/orchestrator path.
- LLM `top_p` is propagated to OpenAI-compatible and llama.cpp payloads.
- LLM request contracts expose `temperature`, `top_p`, `frequency_penalty`, `presence_penalty`, `seed`, and optional `max_tokens`.
- Provider configuration API exposes effective capabilities and frontend-safe runtime controls without exposing API secrets.
- Embedding and reranker request contracts support model-level overrides and output controls.
- Embedding and reranker endpoint paths, health paths, dimensions and top-N defaults are configurable instead of hard-coded.
- llama.cpp runtime configuration covers the advanced CPU, KV-cache, GPU, batching, sampling, speculative-decoding, server, reasoning and model-loading controls needed by the model settings UI.
- Application-side generation limits are optional; no hidden 1024-token generation cap is imposed when the user/model profile does not specify one.
- Context budget output reservation defaults to zero and is explicitly opt-in.

## Memory-first context

- `ContextAllocationPolicy` separates the fixed runtime context ceiling from the selection of conversation, memory, knowledge and tool evidence.
- Persistent memory recall is enabled on every message by default and is bounded by configurable `memory_recall_top_k` (default 5).
- Memory recall is independent of planner semantics: when enabled and a memory retriever exists, it runs for every message rather than only when `plan.memory_required` happens to be true.
- Memory recall happens before context assembly and only selected memories enter the LLM prompt.
- The system does not inject the entire memory database or entire conversation into the model. Retrieval supplies a compact working set, preserving generation speed while providing long-lived effective memory.
- Memory writes/updates/deletes remain model-driven and are not triggered by hard-coded Persian/English phrases.
- Retrieved memory is explicitly marked as durable user-provided facts in the context prompt.

## Agentic tools and verification

- `knowledge.search` exposes the existing hybrid retrieval pipeline as a model-selectable tool.
- Model-selected tool execution records calls and results.
- Knowledge, memory and web evidence can be attached to verification provenance and critic context.
- The complete tool → critic → verifier → revision loop remains intact after the latest telemetry changes.
- Agent execution budgets are passed into the state machine and tool loop.

## Usage accounting and observability

- Agentic provider usage can be marked as already accounted for through response metadata.
- The orchestrator avoids adding provider-reported usage a second time when `usage_recorded=true`.
- Each LLM iteration records provider usage in execution diagnostics.
- The llama.cpp adapter captures optional timing fields (`prompt_n`, prompt timing, predicted/output timing and per-second rates) and raw usage metadata when supplied by the server.
- `/v1/chat` converts diagnostics into a stable `telemetry` object containing context size, prompt/output tokens, estimated prompt tokens, prompt/generation rates and milliseconds, memory matches/tokens, knowledge candidates/tokens, and selected context tokens.
- Chat responses also return the correlated request ID.

## Streaming progress

- The provider-neutral LLM contract exposes incremental `LLMStreamEvent` events.
- The OpenAI-compatible provider streams text and model-selected tool-call fragments over SSE.
- The llama.cpp provider streams text, finish reasons, usage/timing metadata and assembled/validated streamed tool-call arguments.
- This is **provider-level streaming only**. The orchestrator/agentic streaming path is intentionally pending so streaming cannot bypass tool execution, critic, verifier, revision, memory, or execution budgets.

## Browser/API reliability

- FastAPI exposes explicit local CORS configuration through `SUPERAGENT_CORS_ORIGINS`, defaulting to local Vite origins `http://127.0.0.1:3000` and `http://localhost:3000`.
- `/health` is available as a conventional health alias in addition to `/v1/health`.
- The local Express proxy generates/propagates `x-request-id`, logs proxy request/response/error events, and returns structured 503 JSON with the request ID when the API connection fails.
- The proxy timeout remains configurable and defaults to ten minutes so long local generation is not mistaken for a network timeout.

## Verification status

GitHub Actions is configured for Python 3.12 on Linux and Windows plus frontend typecheck/build. The connected GitHub integration currently reports no workflow run for the latest `main` commit, so the latest changes are **not CI-verified**. The local container also cannot reach GitHub/DNS, so I could not clone the repository and run the full suite here. Local llama.cpp performance and end-to-end provider tests must therefore be run on the user's machine.

Focused regression coverage now includes llama.cpp streaming/tool-call assembly, document persistence round-trip/deletion cleanup, and conservative capability/runtime defaults.

## Backend priorities before final frontend work

1. Complete orchestrator/agentic streaming.
2. Normalize and enforce token accounting for generation, tool-driven model calls, critic and verifier stages.
3. Add chat telemetry and proxy failure regression tests.
4. Run and fix the browser/API path with correlated request IDs.
5. Build the first-class safe file ingestion layer.
6. Split knowledge-file and memory-file ingestion workflows over shared primitives.
7. Harden model management/capability discovery.
8. Prove end-to-end agent lifecycle with integration tests.
9. Harden persistence, concurrency, cancellation, idempotency and error mapping.
10. Rebuild the final production frontend only after these backend gates are green.

## Frontend strategy

The active React frontend is a **schematic integration/test client**. It should expose real API behavior, model settings, memory/knowledge state, execution diagnostics and learning flows, but it should not accumulate final-product visual complexity. Its purpose is to make backend testing fast and observable while the backend stabilizes. The final UI will be redesigned from the stable API contracts later.

## Continuation rules

- Inspect existing implementation before creating new components.
- Reuse existing architecture and tests whenever possible.
- Do not duplicate settings, capability resolution, retrieval, memory, or budget logic.
- Remove obsolete parallel implementations only after proving they are not active dependencies.
- Every architectural change must have a focused regression or integration test.
- Do not mark a subsystem complete merely because an endpoint returns HTTP 200; verify the full client-to-provider path and record the evidence.
