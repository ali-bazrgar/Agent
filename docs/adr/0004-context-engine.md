# ADR 0004: Dynamic Context Engine

## Status

Accepted

## Context

The model context window is a temporary working area. The system must not treat it as persistent memory, and it must work across different context sizes.

## Decision

Introduce a dedicated context engine that builds prompt context from the current request, relevant memory, retrieved evidence, tool results, and other state under a configurable token budget. The context engine uses relevance, timestamp, task relevance, uncertainty, and provenance to decide what to include.

## Consequences

- The system avoids overloading the model with irrelevant content.
- The architecture becomes configurable across small and large context windows.
- Context construction becomes explicit, testable, and observable.
