# SuperAgent — Project State

This repository is the canonical implementation of the SuperAgent runtime. This document is the short, durable handoff for continuing work in a fresh chat.

## Current baseline

- Baseline commit: `17b98aebafb2c0c045e5cfcacfeb0927d7e59742`
- Main branch is the source of truth.
- The runtime has model/provider capability resolution, context budgeting, hybrid retrieval, reranking, memory lifecycle components, agent execution budgets, agentic tool execution, and a critic/verifier/revision loop.

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

### Agent execution
- Model-call, tool-call, retry and wall-clock execution budgets exist.
- Tool reservations are enforced before actual tool execution.
- Agentic tool loops are covered by budget tests.
- Critic, verifier and revision stages exist.

### Memory and learning
- Memory extraction/lifecycle/search components exist.
- Learning extraction and scheduling components exist.
- SQLite repositories exist for memory, knowledge, learning and related entities.

## Known blocker at this baseline

A local `pytest` run after pulling `17b98ae` collected 185 tests but failed during collection because `superagent.retrieval.__init__` eagerly imported retrieval backends. That initialization path created this cycle:

`context.models -> retrieval.models -> retrieval.__init__ -> retrieval.memory_backend -> memory.search -> memory.ranking -> context.ports -> context.models`

The current continuation commit fixes this package-initialization cycle by making the retrieval package public API lazy and adds a regression test.

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
