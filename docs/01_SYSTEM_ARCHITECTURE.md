# System Architecture

## Architectural style

The system is a modular monolith with strict internal boundaries. It should not be implemented as a set of independent microservices during the initial phase.

## Core layers

```text
API Layer
  ↓
Application Services
  ↓
Domain / Orchestration
  ↓
Interfaces (ports)
  ↑
Infrastructure Adapters
```

The dependency direction is inward: API and application code may depend on domain services, but domain logic must not depend directly on FastAPI, SQLite, llama.cpp, or a specific vector engine.

## Module boundaries

- `api/`: transport, validation, serialization
- `application/`: use cases and orchestration entry points
- `agents/`: execution roles and orchestration policies
- `memory/`: memory subsystem and memory lifecycle
- `knowledge/`: document and knowledge domain concepts
- `retrieval/`: hybrid retrieval pipeline
- `context/`: dynamic context construction and token budgeting
- `llm/`, `embeddings/`, `reranking/`: provider-adapter modules
- `tools/`, `web/`: tool and web provider abstractions
- `learning/`, `fsrs/`: learning engine and scheduling abstraction
- `database/`: repositories and persistence adapters
- `models/`: shared domain models
- `security/`, `observability/`, `evaluation/`: cross-cutting concerns

## Provider abstraction

The application depends on provider interfaces rather than runtime-specific implementations.

- `LLMProvider`
- `EmbeddingProvider`
- `RerankerProvider`
- `WebResearchProvider`
- `SchedulerProvider` (for FSRS or future alternatives)

The initial implementation may use llama.cpp over HTTP, but llama.cpp is an infrastructure adapter and not part of the domain or application layer.

## Runtime configuration

Runtime configuration is provided through environment variables and config objects. The application never needs GGUF paths, llama.cpp executable paths, or model-specific flags.

Required configuration categories:

- model endpoints and identifiers
- timeouts and retry budgets
- storage paths
- database backend selection
- vector/lexical engine selection
- token budgets and context limits
- security policies and feature flags

## Source-of-truth boundaries

The architecture separates:

- authoritative structured state (relational storage)
- immutable source data (files/blobs)
- derived indexes (vector and lexical)
- runtime state (executions, sessions, working memory)
- cache (disposable performance data)

Derived indexes must be rebuildable from source-of-truth data.

## Failure isolation

Every subsystem must have explicit failure boundaries:

- retrieval failure falls back to available evidence
- embedding failure marks content as pending rather than losing source data
- web research failure returns a structured error without crashing the request
- model provider failure preserves execution state and returns a graceful error

## Execution model

Requests do not always use the full pipeline. The router selects the simplest valid execution path based on request type and budget.

The architecture supports:

- direct LLM response
- retrieval-assisted answer generation
- planning and tool execution
- research workflows
- learning workflows

Example:

```text
RECEIVED
ANALYZING
RETRIEVING
PLANNING
EXECUTING
SYNTHESIZING
CRITIQUING
VERIFYING
FINALIZING
PERSISTING
COMPLETED
FAILED
```

The implementation may use a better state machine if appropriate.

---

# 11. Observability

Every execution must have:

* execution_id
* session_id
* user_id
* timestamps
* model calls
* retrieval operations
* selected memories
* selected sources
* tool calls
* failures
* latency
* token usage

Do not store hidden chain-of-thought.

Store structured operational metadata and concise reasoning summaries instead.
