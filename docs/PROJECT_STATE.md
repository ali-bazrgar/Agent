# SuperAgent — Project State

This repository is the canonical implementation of the SuperAgent runtime. This document is the short, durable handoff for continuing work in a fresh chat.

## Current baseline

- Baseline commit: `a6498c79532799abb85bc34b82eed060ad499487`
- Main branch is the source of truth.
- The runtime has model/provider capability resolution, context budgeting, hybrid retrieval, reranking, memory lifecycle components, agent execution budgets, agentic tool execution, and a critic/verifier/revision loop.

## Latest local verification

After pulling the documentation/dependency-boundary cleanup commit, the local Windows environment collected **188 tests**.

- **187 passed**
- **1 failed** in `tests/unit/test_retrieval_service.py`
- Failure cause: `RetrievalOrchestrator` constructed backend `RetrievalQuery` objects with `token_budget=None` even when the service-level budget was supplied.
- Fixed in commit `a6498c79532799abb85bc34b82eed060ad499487`.
- The fix propagates the requested global token budget through each backend query while retaining the orchestrator's post-merge global budget enforcement as the authoritative final constraint.

The next local run should be used to confirm the resulting baseline is fully green.

## Verified work already implemented

### Runtime and context
- Model/provider capabilities are resolved into effective runtime limits.
- Effective context is bounded by model and provider capabilities.
- Effective output is bounded by model/provider limits and context capacity.
- Context construction has token budgeting, ranking, deduplication and adaptive trimming.

### Retrieval
- Dense and lexical retrieval are available.
- Hybrid fusion and global ranking are implemented.
- Retrieval orchestration and retrieval budgets are present.
- Memory retrieval has a dedicated backend/search path.
- Retrieval package initialization is lazy so importing retrieval models does not eagerly load memory/context dependencies.

### Agent execution
- Model-call, tool-call, retry and wall-clock execution budgets exist.
- Tool reservations are enforced before actual tool execution.
- Agentic tool loops are covered by budget tests.
- Critic, verifier and revision stages exist.

### Memory and learning
- Memory extraction/lifecycle/search components exist.
- Learning extraction and scheduling components exist.
- SQLite repositories exist for memory, knowledge, learning and related entities.

## Documentation / continuation baseline

The previous large collection of overlapping Markdown specifications was consolidated into three canonical documents:

- `docs/PROJECT_STATE.md` — current implementation state and next priorities.
- `docs/ARCHITECTURE_MAP.md` — current architecture and dependency boundaries.
- `docs/CONTINUATION_PROTOCOL.md` — procedure for safely continuing the project in a fresh chat.

Git history remains the implementation source of truth; these documents are durable navigation/handoff aids and must be kept synchronized with material architectural changes.

## Next engineering priorities

1. Complete provider/runtime wiring so every LLM provider consumes one resolved `ModelRuntimeConfig` instead of independently reading Settings.
2. Add model input/output token accounting to execution budgets.
3. Verify the relationship between Agent context budget and actual llama.cpp `--ctx-size`; do not treat the two as the same thing.
4. Prove end-to-end `Generation -> Critic -> Verification -> Revision` behavior with real failure/revision cases.
5. Verify the full `retrieval -> context -> generation -> memory` lifecycle.
6. Continue hardening integration tests before claiming production readiness.

## Rules for future continuation

- Inspect existing implementation before creating new components.
- Reuse existing architecture and tests whenever possible.
- Do not duplicate settings, capability resolution, retrieval, memory, or budget logic.
- Every architectural change must have a focused regression/integration test.
- Do not claim a subsystem is production-ready until its real integration path is tested.
