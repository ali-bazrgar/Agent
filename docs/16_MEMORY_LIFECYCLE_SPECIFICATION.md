# Memory Lifecycle Specification (Phase 6)

## Overview
The Memory Lifecycle subsystem processes conversation interactions, extracts structured memory candidates, validates them against configurable policies, consolidates them against existing stored memories to prevent duplicates, ranks them by relevance and confidence, and persists them for future retrieval.

## Memory Architecture

### 1. Memory Models (`src/superagent/memory/models.py`)
- **`MemoryCandidate`**: Candidate memory extracted from conversation turn with `kind`, `importance`, `confidence`, and `relevance`.
- **`MemoryPolicy`**: Configurable thresholds (`min_confidence`, `min_importance`, `allowed_kinds`).
- **`ConsolidationResult`**: Outcome of consolidation (`CREATED`, `MERGED`, `SUPERSEDED`, `IGNORED`).

### 2. Extractor (`src/superagent/memory/extraction.py`)
- Identifies facts, user preferences, names, and explicit instructions.
- Ignores trivial conversation noise (greetings, simple acknowledgements).

### 3. Consolidator (`src/superagent/memory/consolidation.py`)
- `MERGED`: Matches exact or high-similarity existing memories and boosts confidence score.
- `SUPERSEDED`: Replaces outdated user facts (e.g. updated user name or preferences).
- `CREATED`: Persists new distinct memories.

### 4. Memory Ranking & Retriever (`src/superagent/memory/ranking.py`)
- `MemoryRanker`: Ranks memory records using query match, confidence, importance, and relevance.
- `DefaultMemoryRetriever`: Adapter implementing `MemoryRetrieverPort` for seamless integration into `ContextEngine`.

### 5. Memory Lifecycle Pipeline (`src/superagent/memory/lifecycle.py`)
- `MemoryLifecycle`: Coordinates `Extractor -> Policy Validation -> Consolidator -> Persistence`.
