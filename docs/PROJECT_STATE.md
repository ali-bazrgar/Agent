# SuperAgent — Project State

This repository is the canonical implementation of the SuperAgent runtime. This document is the durable handoff for continuing backend work before the frontend is rebuilt.

## Current baseline

- `main` baseline: `ca6e804cf9bd8866ba23000c72dd81d8c542c38a`
- Active hardening branch: `hardening/runtime-wiring-and-agent-routing`
- Current branch head is tracked by PR #8.
- The backend already contains model/provider capability resolution, context budgeting, hybrid retrieval, reranking, memory lifecycle components, learning components, execution budgets, model-selected tool execution, critic/verifier/revision stages, and SQLite persistence.

## Important architectural decision

The default agentic path is **model-driven**. Natural-language keyword matching must not decide whether a user asked to save memory, search knowledge, browse the web, calculate something, or use another tool. The LLM receives the available tool schemas and may select zero or more tools. Deterministic routing remains only as an explicit compatibility mode when `llm_driven_tools=false`.

## Work completed on the current hardening branch

### Runtime and model controls
- One effective LLM runtime configuration is resolved at the application composition root and injected into the provider/orchestrator path.
- LLM `top_p` is propagated to OpenAI-compatible and llama.cpp payloads.
- LLM request contracts now expose `temperature`, `top_p`, `frequency_penalty`, `presence_penalty`, `seed`, and `max_tokens`.
- Provider configuration API exposes effective capabilities and frontend-safe runtime controls without exposing API secrets.
- Embedding and reranker request contracts support model-level overrides and output controls.
- Embedding and reranker endpoint paths, health paths, dimensions and top-N defaults are now configurable instead of hard-coded.

### Agentic tools and verification
- `knowledge.search` exposes the existing hybrid retrieval pipeline as a model-selectable tool.
- Model-selected tool execution records both calls and tool results.
- Knowledge, memory and web tool evidence can be attached to verification provenance and critic context.
- Agent execution budgets are passed into the state machine and tool loop.

### API surface
- `/v1/config` and `/v1/config/models` expose the model/runtime surface needed by the future frontend settings UI.
- Existing document ingestion API remains the canonical ingestion path.
- Chat attachments have bounded request/file sizes and are passed through the agent context path.

## Verification status

GitHub Actions is configured for Python 3.12 on Linux and Windows plus frontend typecheck/build. The current environment cannot execute the repository locally and the latest branch head has not yet produced a workflow result through the available GitHub status interface. Therefore this branch is **not yet declared production-ready**.

## Backend priorities before frontend work

1. Finish real token accounting: prompt, output, tool-call, critic and verifier usage must consume explicit execution/context budgets.
2. Complete streaming at the **orchestrator/agentic-provider level**, not by bypassing tools, critic or verification. The future chat UI will depend on this.
3. Build a first-class file ingestion layer for uploaded files, including safe type detection, size limits, extraction, provenance, hashing/deduplication and asynchronous ingestion status.
4. Make knowledge-file ingestion and memory-file ingestion separate, explicit workflows while sharing the same safe file/extraction primitives.
5. Complete model management/configuration for LLM, embedding and reranker providers, including capability discovery, validation, health, model identity and safe runtime overrides.
6. Prove end-to-end `Generation -> Tool Selection -> Tool Execution -> Critic -> Verification -> Revision -> Memory` behavior with integration tests.
7. Harden persistence, concurrency, cancellation, idempotency, error mapping and observability.
8. Only after the backend gates above are green, rebuild the frontend around the stable API contract.

## Planned frontend scope after backend completion

The frontend will be treated as a separate product layer rather than driving backend design prematurely. It is planned to include a professional chat workspace, advanced composer/attachment handling, knowledge and memory management, execution/provenance views, learning/review surfaces, and comprehensive LLM/embedding/reranker settings backed by the APIs above.

## Continuation rules

- Inspect existing implementation before creating new components.
- Reuse existing architecture and tests whenever possible.
- Do not duplicate settings, capability resolution, retrieval, memory, or budget logic.
- Every architectural change must have a focused regression or integration test.
- Do not claim a subsystem is production-ready until its real integration path is tested.
- Do not start the final frontend rebuild until the backend contract and integration gates are stable.
