# ADR 0003: Memory Model

## Status

Accepted

## Context

The system needs durable memory that is more structured than raw chat history. Memory must support explicit facts, inferred hypotheses, and temporal state without collapsing them together.

## Decision

Design memory as a dedicated subsystem with layered memory types and a Personal Knowledge Model. The architecture separates:

- Working memory
- Session memory
- Episodic memory
- Semantic memory
- Procedural memory
- User memory
- Temporal memory

Every durable memory carries provenance, confidence, importance, relevance, validity, and status. Explicit facts and inferred hypotheses are stored distinctly.

## Consequences

- Memory becomes reusable and auditable.
- The system can manage memory lifecycle, consolidation, expiration, and supersession explicitly.
- The model is not allowed to silently promote inference to fact.
