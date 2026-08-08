# ADR 0001: Storage Strategy

## Status

Accepted

## Context

The platform needs authoritative structured state, immutable source documents, derived indexes, and runtime state. No single storage technology is sufficient for all of these concerns.

## Decision

Use a layered storage approach:

- relational storage for authoritative structured state
- file/object storage for original documents and immutable source artifacts
- vector index for derived embeddings
- lexical index for derived full-text data
- cache for disposable performance data

The initial implementation uses SQLite for relational storage, but repository interfaces remain backend-agnostic so PostgreSQL can be adopted later.

## Consequences

- The architecture remains local-first and simple.
- Derived data can be rebuilt from source-of-truth data.
- The storage model is extensible but still understandable.
