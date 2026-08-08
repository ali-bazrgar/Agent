# ADR 0002: Provider Abstraction

## Status

Accepted

## Context

The application must remain independent from a specific model runtime, model file layout, or model vendor.

## Decision

Introduce provider interfaces for model runtime concerns:

- `LLMProvider`
- `EmbeddingProvider`
- `RerankerProvider`
- `WebResearchProvider`

The initial implementation may use llama.cpp over HTTP, but the domain and application layers depend only on provider interfaces and configuration.

## Consequences

- The application layer remains portable across runtime backends.
- Model runtime changes do not require business logic rewrites.
- Testing becomes easier through mock providers.
