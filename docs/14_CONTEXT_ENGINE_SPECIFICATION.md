# Phase 5 — Context Engine & Prompt Construction Specification

## Overview

The **Context Engine** (`src/superagent/context/`) is responsible for transforming raw conversation state, memories, retrieved knowledge candidates (from `HybridRetriever`), and system instructions into a bounded, deterministic, model-ready prompt context.

It serves as the decoupling layer between storage/retrieval providers and future agent orchestrators or LLM completions.

---

## Core Architecture & Components

```
ContextRequest
     │
     ▼
┌────────────────────────────────────────────────────────┐
│ ContextEngine                                          │
│                                                        │
│  1. Convert inputs to ContextItems                     │
│  2. Deduplicate (chunk_id, memory_id, content hash)    │
│  3. Deterministic Sorting (priority, score, item_id)   │
│  4. Budget Manager Allocation (Tokens Invariant)       │
│  5. Re-establish Chronological Order                   │
│  6. PromptBuilder (System message, History, Query)     │
└────────────────────────────────────────────────────────┘
     │
     ▼
ContextBuildResult (prompt_messages, selection, provenance)
```

### Module Structure

- **`models.py`**: Domain models (`ContextRequest`, `ContextItem`, `ChatMessage`, `ContextBudget`, `ContextSelection`, `ContextBuildResult`).
- **`ports.py`**: Port abstractions (`ContextEnginePort`, `MemoryRetrieverPort`).
- **`budget.py`**: Token estimation (`TokenEstimator`) and context window budget tracking (`ContextBudgetManager`).
- **`ranking.py`**: Deduplication (`deduplicate_context_items`) and deterministic priority sorting (`sort_context_items_deterministically`).
- **`prompt.py`**: Structured message formatting (`PromptBuilder`).
- **`builder.py`**: Orchestration logic (`ContextEngine`).

---

## Priority & Determinism Matrix

Context items are categorized by `ContextItemKind` and assigned deterministic priorities:

| Item Kind | Priority | Behavior |
| :--- | :--- | :--- |
| `SYSTEM_INSTRUCTION` | 10 | System instructions & base directives |
| `USER_QUERY` | 20 | **Mandatory**. Current user query (never dropped) |
| `CONVERSATION_MESSAGE` (Recent) | 30 | Last 4 conversation turns |
| `KNOWLEDGE_CHUNK` | 40 | Retrieved knowledge candidate chunks |
| `MEMORY` | 50 | Relevant long-term/session memory records |
| `CONVERSATION_MESSAGE` (Older) | 60 | Older historical conversation turns |

### Deterministic Tie-Breaking
When multiple items compete for space within the same budget, they are sorted using:
`key = (item.priority, -item.score, item.item_id)`

This guarantees 100% deterministic prompt output across identical execution inputs.

---

## Token Budgeting Invariant

The Context Engine strictly guarantees the fundamental context window invariant:

$$\text{Total Prompt Tokens} + \text{Reserved Output Tokens} \le \text{Total Context Window}$$

- **Default Window**: 8,192 tokens.
- **Default Reserved Output**: 1,024 tokens.
- **Available Prompt Tokens**: $8,192 - 1,024 = 7,168$ tokens.

If candidate items exceed the available prompt budget, lower-priority items are trimmed and recorded in `selection.dropped_items`. The current user query is mandatory and will raise a `ValidationError` if the query itself exceeds the available prompt budget.

---

## Provenance Preservation

Every knowledge chunk or memory item selected for inclusion in the prompt retains full provenance:

- `source_id`
- `document_id`
- `version_id`
- `chunk_id`
- `memory_id`
- `retrieval_method` (`dense`, `lexical`, `rrf`, `reranked`)
- `score` (similarity or reranker score)
- `provenance` metadata dictionary

The provenance records are exposed directly in `ContextBuildResult.provenance` for auditing, debugging, and downstream citation rendering.

---

## Token Estimation & Future Model Tokenizers

- **Current Implementation**: Uses a deterministic character-ratio estimator ($\sim 4$ characters per token + framing overhead) matching `TextChunker`.
- **Extensibility**: `TokenEstimator` accepts an optional `tokenizer_fn: Callable[[str], int]` override, allowing model-specific tokenizers (such as `tiktoken` or llama.cpp tokenizers) to be injected when required.

---

## Verification & Test Results

The Context Engine suite (`tests/test_context_engine.py`) covers:
1. Token budget calculation & invariant enforcement
2. Mandatory user query preservation
3. System instruction & context section formatting
4. Knowledge & memory deduplication and ranking
5. Budget overflow trimming & dropped item tracking
6. Deterministic tie-breaking
7. Empty retrieval & memory handling
8. Cosine similarity score clamping regression
9. AppContainer wireup

**Test Results**: 57/57 tests passing.
