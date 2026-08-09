# SuperAgent — Project State

This repository is the canonical implementation of the SuperAgent runtime. This document is the durable handoff for continuing backend work before the frontend is rebuilt.

## Current baseline

- `main` is the canonical integration branch.
- The backend already contains model/provider capability resolution, context budgeting, hybrid retrieval, reranking, persistent memory lifecycle components, learning components, execution budgets, model-selected tool execution, critic/verifier/revision stages, and SQLite persistence.

## Important architectural decisions

The default agentic path is **model-driven** for semantic actions. Natural-language keyword matching must not decide whether a user asked to save memory, search knowledge, browse the web, calculate something, or use another tool. The LLM receives the available tool schemas and may select zero or more tools. Deterministic routing remains only as an explicit compatibility mode.

Persistent memory **recall** is different from semantic memory writes. Every user turn performs a bounded, relevance-ranked lookup against persistent memory before context construction by default. This gives a small-context model access to durable user facts without replaying the full conversation. The LLM still decides whether to create, update, consolidate, or delete memories through the memory tool/lifecycle path.

The target architecture is therefore a fixed user-selected runtime context (for example 8K, 32K, or 128K) combined with retrieval-backed effective memory. The context is not allowed to grow monotonically with the conversation. The database is the long-term memory; the LLM context is a temporary working set containing only relevant evidence.

## Work completed on the current hardening path

### Runtime and model controls
- One effective LLM runtime configuration is resolved at the application composition root and injected into the provider/orchestrator path.
- LLM `top_p` is propagated to OpenAI-compatible and llama.cpp payloads.
- LLM request contracts expose `temperature`, `top_p`, `frequency_penalty`, `presence_penalty`, `seed`, and optional `max_tokens`.
- Provider configuration API exposes effective capabilities and frontend-safe runtime controls without exposing API secrets.
- Embedding and reranker request contracts support model-level overrides and output controls.
- Embedding and reranker endpoint paths, health paths, dimensions and top-N defaults are configurable instead of hard-coded.
- llama.cpp runtime configuration covers the advanced CPU, KV-cache, GPU, batching, sampling, speculative-decoding, server, reasoning and model-loading controls needed by the future model settings UI.
- Application-side generation limits are optional; no hidden 1024-token generation cap is imposed when the user/model profile does not specify one.
- Context budget output reservation now defaults to zero and is explicitly opt-in.

### Memory-first context
- `ContextAllocationPolicy` separates the fixed runtime context ceiling from the selection of conversation, memory, knowledge and tool evidence.
- Persistent memory recall is enabled on every message by default and is bounded by a configurable `memory_recall_top_k` (default 5).
- Memory recall happens before context assembly and only the selected memories enter the LLM prompt.
- The system does not inject the entire memory database or entire conversation into the model. Retrieval supplies a compact working set, preserving generation speed while providing long-lived effective memory.
- Memory writes/updates/deletes remain model-driven and are not triggered by hard-coded Persian/English phrases.

### Agentic tools and verification
- `knowledge.search` exposes the existing hybrid retrieval pipeline as a model-selectable tool.
- Model-selected tool execution records both calls and tool results.
- Knowledge, memory and web tool evidence can be attached to verification provenance and critic context.
- Agent execution budgets are passed into the state machine and tool loop.

### Usage accounting hardening
- Agentic provider usage can be marked as already accounted for through response metadata.
- The orchestrator now avoids adding provider-reported usage a second time when `usage_recorded=true`.
- A regression test locks this contract so provider-side accounting cannot silently become duplicate execution-level accounting again.
- The implementation was also cleaned so the critic state transition uses the canonical `CRITIQUING` status directly.

### Runtime observability hardening
- The diagnostic store now supports structured operation spans with `operation.started` and `operation.finished` events.
- Every finished span records measured wall-clock duration and success/error status; provider failures record their exception type without swallowing the original exception.
- Diagnostic spans carry execution/request correlation IDs and pass through the existing secret-scrubbing layer.
- Regression tests cover both successful and failed spans.
- This is the instrumentation primitive for the next stage: wiring separate spans around LLM generation, embedding, reranking, memory recall, retrieval, tool execution, critic and verifier calls so TTFT/generation tok/s and subsystem latency can be measured independently.

### API surface
- `/v1/config` and `/v1/config/models` expose the model/runtime surface needed by the future frontend settings UI.
- Existing document ingestion API remains the canonical ingestion path.
- Chat attachments have bounded request/file sizes and are passed through the agent context path.

## Verification status

GitHub Actions is configured for Python 3.12 on Linux and Windows plus frontend typecheck/build. Repository changes must be validated by CI and, where available, by real local runtime tests against llama.cpp. The current environment cannot execute the user's local llama.cpp installation, so local tok/s measurements must be taken by the user and correlated with Agent diagnostics. The latest backend hardening commits have not yet produced a new CI run in the connected GitHub Actions view, so they must not be described as CI-verified until a run is available.

## Backend priorities before frontend work

1. Finish real token accounting: prompt, output, tool-call, critic and verifier usage must consume explicit execution/context budgets.
2. Complete streaming at the **orchestrator/agentic-provider level**, not by bypassing tools, critic or verification. The future chat UI will depend on this.
3. Build a first-class file ingestion layer for uploaded files, including safe type detection, size limits, extraction, provenance, hashing/deduplication and asynchronous ingestion status.
4. Make knowledge-file ingestion and memory-file ingestion separate, explicit workflows while sharing the same safe file/extraction primitives.
5. Complete model management/configuration for LLM, embedding and reranker providers, including capability discovery, validation, health, model identity and safe runtime overrides.
6. Prove end-to-end `Generation -> Tool Selection -> Tool Execution -> Critic -> Verification -> Revision -> Memory` behavior with integration tests.
7. Harden persistence, concurrency, cancellation, idempotency, error mapping and observability.
8. Wire operation spans through all major runtime providers and expose a compact execution-performance summary so regressions can be diagnosed rather than guessed.
9. Only after the backend gates above are green, rebuild the frontend around the stable API contract.

## Planned frontend scope after backend completion

The frontend will be treated as a separate product layer rather than driving backend design prematurely. It is planned to include a professional chat workspace, advanced composer/attachment handling, knowledge and memory management, execution/provenance views, learning/review surfaces, and comprehensive LLM/embedding/reranker settings backed by the APIs above.

## Continuation rules

- Inspect existing implementation before creating new components.
- Reuse existing architecture and tests whenever possible.
- Do not duplicate settings, capability resolution, retrieval, memory, or budget logic.
- Every architectural change must have a focused regression or integration test.
