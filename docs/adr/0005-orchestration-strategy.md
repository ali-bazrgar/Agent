# ADR 0005: Adaptive Orchestration Strategy

## Status

Accepted

## Context

Not every request needs the full planning, retrieval, critique, and verification pipeline. A fixed prompt chain would waste model calls and make the system less responsive.

## Decision

Use adaptive orchestration with a router that selects the simplest valid execution path. The system supports direct response, retrieval-assisted generation, planning, research flows, and learning flows. Every execution uses explicit budgets for model calls, tool calls, retries, execution time, and context tokens.

## Consequences

- Simple requests remain cheap.
- Complex requests can use deeper reasoning when justified.
- The orchestrator remains bounded, observable, and testable.
