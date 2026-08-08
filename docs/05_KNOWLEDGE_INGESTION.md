# Knowledge Ingestion

## Durable ingestion pipeline

The ingestion pipeline is responsible for turning external content into durable knowledge that can be embedded, indexed, queried, and traced back to the original source.

## Pipeline

```text
Source acquisition
  ↓
Validation
  ↓
Parsing
  ↓
Normalization
  ↓
Document creation
  ↓
Chunking
  ↓
Metadata extraction
  ↓
Embedding
  ↓
Lexical indexing
  ↓
Vector indexing
  ↓
Entity / fact extraction (optional)
  ↓
Relationship extraction (optional)
  ↓
Quality validation
  ↓
Ready
```

## Source-of-truth model

The original source document is authoritative. Derived artifacts such as chunks, embeddings, summaries, facts, and indexes are rebuildable from the source document and its associated metadata.

## Knowledge objects

The domain should support separate representations for:

- Document
- Chunk
- Source
- Entity
- Fact
- Relationship
- Summary
- Citation

## Provenance

Every derived artifact must preserve provenance through:

```text
Source → Document → Chunk → Extracted Fact → Memory / Knowledge / Flashcard
```

## Reprocessing and versioning

Changes to the original document must trigger reprocessing or re-indexing as appropriate. Derived artifacts should be versioned so they can be rebuilt or invalidated without losing the original source.

## Incremental processing

Large ingestion jobs must be processed incrementally. The architecture should support:

- queued state
- processing state
- completed state
- failed state

## Quality validation

The ingestion workflow should validate:

- parse success
- content length
- chunk viability
- embedding success
- indexing success
- extraction quality

## User-initiated knowledge

Knowledge that the user explicitly asks to save is treated as a stronger persistence signal, but it still preserves provenance and correction/deletion support.
