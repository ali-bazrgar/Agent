# RAG Architecture

## Retrieval as a hybrid subsystem

The system must not rely on vector search alone. Retrieval is a staged pipeline that combines dense, lexical, metadata, and temporal signals before evidence is passed to the context engine.

## Retrieval pipeline

```text
Query Understanding
  ↓
Metadata / Temporal Filtering
  ↓
Dense Retrieval
  ↓
Lexical Retrieval
  ↓
Candidate Fusion
  ↓
Reranking
  ↓
Evidence Selection
  ↓
Context Compression
  ↓
Context Assembly
```

## Query understanding

The query processor should derive:

- semantic query
- keywords
- entities
- temporal constraints
- source constraints
- user context
- required retrieval depth

## Candidate generation

The system supports multiple retrieval paths:

- dense vector retrieval
- lexical/full-text retrieval
- metadata filtering
- temporal filtering
- optional graph-style relationship traversal for future use

## Candidate fusion

Results from multiple retrievers must be merged by an explicit fusion rule such as Reciprocal Rank Fusion or weighted rank fusion. Raw scores from different retrievers are not assumed to be directly comparable.

## Reranking

Top-N candidates are reranked by an independent reranker provider. The reranker is not a hard-coded model; it is selected through configuration and provider abstraction.

## Evidence selection

The retrieval subsystem produces a small, sufficient evidence set that is ranked and attributed. This evidence set is then handed to the context engine.

## Context compression

If the evidence set is too large for the current model budget, the context engine compresses it while preserving provenance and source attribution.

## Metadata and provenance

Every chunk should support metadata such as:

- document_id
- source
- title
- section
- page
- position
- language
- created_at
- updated_at
- content_hash
- chunk_hash

Every generated claim, flashcard, and answer should preserve provenance back to source documents and chunks where possible.

## Deduplication and rebuildability

The system must avoid re-embedding identical content and must allow derived indexes to be rebuilt from source-of-truth data.
