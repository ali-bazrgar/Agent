# SuperAgent — Project State

This repository is the canonical implementation of the SuperAgent runtime. This document is the durable handoff for continuing backend work before the frontend is rebuilt.

## Current baseline

- `main` is the canonical integration branch.
- The backend contains model/provider capability resolution, context budgeting, hybrid retrieval, reranking, persistent memory lifecycle components, learning components, execution budgets, model-selected tool execution, critic/verifier/revision stages, and SQLite persistence.

## Important architectural decisions

The default agentic path is **model-driven** for semantic actions. Natural-language keyword matching must not decide whether a user asked to save memory, search knowledge, browse the web, calculate something, or use another tool. The LLM receives the available tool schemas and may select zero or more tools. Deterministic routing remains only as an explicit compatibility mode.

Persistent memory **recall** is different from semantic memory writes. Every user turn performs a bounded, relevance-ranked lookup against persistent memory before context construction by default. This gives a small-context model access to durable user facts without replaying the full conversation. The LLM still decides whether to create, update, consolidate, or delete memories through the memory tool/lifecycle path.

The target architecture is a fixed user-selected runtime context (for example 8K, 32K, or 128K) combined with retrieval-backed effective memory. The context is not allowed to grow monotonically with the conversation. The database is the long-term memory; the LLM context is a temporary working set containing only relevant evidence.

## Backend hardening completed so far

### Runtime and model controls
- One effective LLM runtime configuration is resolved at the application composition root and injected into the provider/orchestrator path.
- LLM `top_p` is propagated to OpenAI-compatible and llama.cpp payloads.
- LLM request contracts expose `temperature`, `top_p`, `frequency_penalty`, `presence_penalty`, `seed`, and optional `max_tokens`.
- Provider configuration API exposes effective capabilities and frontend-safe runtime controls without exposing API secrets.
- Embedding and reranker request contracts support model-level overrides and output controls.
- Embedding and reranker endpoint paths, health paths, dimensions and top-N defaults are configurable instead of hard-coded.
- llama.cpp runtime configuration covers the advanced CPU, KV-cache, GPU, batching, sampling, speculative-decoding, server, reasoning and model-loading controls needed by the model settings UI.
- Application-side generation limits are optional; no hidden 1024-token generation cap is imposed when the user/model profile does not specify one.
- Context budget output reservation defaults to zero and is explicitly opt-in.

### Memory-first context
- `ContextAllocationPolicy` separates the fixed runtime context ceiling from the selection of conversation, memory, knowledge and tool evidence.
- Persistent memory recall is enabled on every message by default and is bounded by configurable `memory_recall_top_k` (default 5).
- Memory recall is independent of planner semantics: when enabled and a memory retriever exists, it runs for every message rather than only when `plan.memory_required` happens to be true.
- Memory recall happens before context assembly and only selected memories enter the LLM prompt.
- The system does not inject the entire memory database or entire conversation into the model. Retrieval supplies a compact working set, preserving generation speed while providing long-lived effective memory.
- Memory writes/updates/deletes remain model-driven and are not triggered by hard-coded Persian/English phrases.
- Retrieved memory is explicitly marked as durable user-provided facts in the context prompt.

### Agentic tools and verification
- `knowledge.search` exposes the existing hybrid retrieval pipeline as a model-selectable tool.
- Model-selected tool execution records calls and results.
- Knowledge, memory and web evidence can be attached to verification provenance and critic context.
- The complete tool → critic → verifier → revision loop remains intact after the latest telemetry changes.
- Agent execution budgets are passed into the state machine and tool loop.

### Usage accounting and observability
- Agentic provider usage can be marked as already accounted for through response metadata.
- The orchestrator avoids adding provider-reported usage a second time when `usage_recorded=true`.
- A regression test locks this contract so provider-side accounting cannot silently become duplicate execution-level accounting again.
- Diagnostic spans cover routing, planning, tool/research execution, memory recall, knowledge retrieval, context construction, LLM generation, critic, verifier and memory processing.
- Each LLM iteration records the provider token-usage object in execution diagnostics.
- The llama.cpp adapter captures optional timing fields (`prompt_n`, prompt timing, predicted/output timing and per-second rates).
- `/v1/chat` now converts those diagnostics into a stable `telemetry` object containing context size, prompt/output tokens, estimated prompt tokens, prompt/generation rates and milliseconds, memory matches/tokens, knowledge candidates/tokens, and selected context tokens.
- Chat responses also return the correlated request ID.

### Streaming progress
- The provider-neutral LLM contract already exposes incremental `LLMStreamEvent` events.
- The OpenAI-compatible provider already streams text and model-selected tool-call fragments over SSE.
- The llama.cpp provider now has the same SSE streaming behavior, including incremental text, finish reasons, usage/timing metadata, and assembly/validation of streamed tool-call arguments.
- This is **provider-level streaming only**. The orchestrator/agentic streaming path is intentionally still pending so streaming cannot bypass tool execution, critic, verifier, revision, memory, or execution budgets.

### Browser/API reliability
- FastAPI exposes explicit local CORS configuration through `SUPERAGENT_CORS_ORIGINS`, defaulting to local Vite origins `http://127.0.0.1:3000` and `http://localhost:3000`.
- `/health` is available as a conventional health alias in addition to `/v1/health`.
- The local Express proxy now generates/propagates `x-request-id`, logs proxy request/response/error events, and returns structured 503 JSON with the request ID when the API connection fails.
- The proxy timeout remains configurable and defaults to ten minutes so long local generation is not mistaken for a network timeout.

## Verification status

GitHub Actions is configured for Python 3.12 on Linux and Windows plus frontend typecheck/build. Repository changes must be validated by CI and, where available, by real local runtime tests against llama.cpp. The connected environment cannot execute the user's local llama.cpp installation, so local tok/s measurements must be taken by the user and correlated with Agent diagnostics. Do not call these changes CI-verified until a successful run exists for the relevant commit.

The latest provider-streaming implementation was committed to `main`, and focused regression coverage was added for llama.cpp text streaming and streamed tool-call argument assembly. CI visibility from the connected GitHub integration currently reports no workflow run for the latest commit, so this work is **not marked CI-verified** yet.

## Backend priorities before frontend work

1. Run the browser/API path with correlated request IDs and eliminate the remaining `Failed to fetch` condition based on actual proxy and FastAPI evidence.
2. Add regression coverage for the chat telemetry contract and proxy failure behavior.
3. Complete real token accounting: prompt, output, tool-call, critic and verifier usage must consume explicit execution/context budgets.
4. Complete streaming at the **orchestrator/agentic-provider level**, not by bypassing tools, critic or verification.
5. Build a first-class file ingestion layer for uploaded files, including safe type detection, size limits, extraction, provenance, hashing/deduplication and asynchronous ingestion status.
6. Make knowledge-file ingestion and memory-file ingestion separate, explicit workflows while sharing the same safe file/extraction primitives.
7. Complete model management/configuration for LLM, embedding and reranker providers, including capability discovery, validation, health, model identity and safe runtime overrides.
8. Prove end-to-end `Generation -> Tool Selection -> Tool Execution -> Critic -> Verification -> Revision -> Memory` behavior with integration tests.
9. Harden persistence, concurrency, cancellation, idempotency, error mapping and observability.
10. Only after the backend gates above are green, rebuild the frontend around the stable API contract.

## Planned frontend scope after backend completion

The frontend will be treated as a separate product layer rather than driving backend design prematurely. It is planned to include a professional chat workspace, advanced composer/attachment handling, knowledge and memory management, execution/provenance views, learning/review surfaces, and comprehensive LLM/embedding/reranker settings backed by the APIs above.

## Continuation rules

- Inspect existing implementation before creating new components.
- Reuse existing architecture and tests whenever possible.
- Do not duplicate settings, capability resolution, retrieval, memory, or budget logic.
- Every architectural change must have a focused regression or integration test.
- Do not mark a subsystem complete merely because an endpoint returns HTTP 200; verify the full client-to-provider path and record the evidence.
