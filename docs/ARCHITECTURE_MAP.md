# SuperAgent — Architecture Map

## Runtime flow

```text
User Request
    |
    v
Agent Orchestrator
    |
    +--> Runtime Policy / Effective Capabilities
    |        |
    |        +--> ModelRuntimeConfig
    |        +--> execution budgets
    |
    +--> Retrieval Orchestrator
    |        |
    |        +--> lexical retrieval
    |        +--> dense retrieval
    |        +--> hybrid fusion
    |        +--> global ranking / reranking
    |        +--> memory retrieval
    |
    +--> Context Engine
    |        |
    |        +--> candidate ranking
    |        +--> deduplication
    |        +--> token budget
    |        +--> adaptive trimming
    |
    +--> LLM Provider
    |        |
    |        +--> generation
    |        +--> optional agentic tool loop
    |
    +--> Critic
    |        |
    |        +--> Verifier
    |        +--> Revision
    |
    +--> Memory / Learning lifecycle
```

## Dependency direction

Low-level domain models and contracts should not import high-level orchestration packages. Package `__init__.py` files must not eagerly import an entire subsystem when a submodule can be imported independently.

The retrieval package therefore exposes its public API lazily. This prevents importing `superagent.context.models` from triggering retrieval backends and memory ranking during package initialization.

## Context and model limits

The intended single source of truth is:

```text
Model capability
        +
Provider capability
        +
User/runtime policy
        |
        v
Effective Runtime Config
        |
        +--> Context Engine prompt budget
        +--> LLM request max output
        +--> provider/backend constraints
```

Agent context budget and actual backend KV-cache capacity are related but distinct. The latter must be verified/configured at the provider/runtime level, especially for llama.cpp.

## Retrieval policy

Retrieval should be query-driven rather than a fixed top-k dump. The pipeline may combine lexical and dense evidence, fuse candidates, apply global ranking/reranking, deduplicate, and finally allocate the context budget according to relevance and source priority.

## Memory policy

Memory is persisted data, not permanent prompt text. Relevant memories should be retrieved and ranked at execution time. The Context Engine decides what enters the current prompt.

## Agent correction policy

The intended correction loop is:

```text
Generation
   -> Critic
   -> Evidence Verification
   -> PASS -> final answer
   -> FAIL -> Revision -> Generation
```

Verification must evaluate claims against actual evidence rather than treating the existence of provenance metadata as proof of support.
