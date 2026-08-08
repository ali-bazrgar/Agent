# Super Agent — Implementation Instructions

You are the lead architect and implementation engineer for the Super Agent project.

## Mission

Build and maintain a modular, local-first AI orchestration platform. Production implementation is in scope. Do not stop at architecture documents when a requested feature requires code.

## Architecture

- Keep domain/application code independent from model-runtime, HTTP, filesystem, and database implementation details.
- Treat LLM context as temporary working memory; durable memory belongs in the memory subsystem.
- Use provider interfaces for LLM, embeddings, reranking, and web research.
- Preserve provenance from source documents through chunks, retrieval, context, memory, and learning artifacts.
- Use deterministic logic for validation, hashing, ranking, scheduling, and state transitions.
- Keep configuration in typed settings/environment variables rather than hard-coded machine-specific paths.
- Prefer a modular monolith with clear boundaries so components can be extracted later.

## Engineering rules

- Python requires 3.12+.
- Frontend uses React, Vite, and TypeScript.
- Every production change must preserve or extend the test suite.
- Run Python compilation/tests and frontend typecheck/build before considering a change complete.
- Avoid broad exception swallowing. Errors must be observable and actionable.
- Do not log secrets, prompts containing sensitive data, API keys, or filesystem contents unnecessarily.
- Keep public API behavior explicit and backwards-compatible unless a breaking change is intentional and documented.
- Do not introduce a dependency without adding it to the appropriate manifest.
- Keep Docker and local-development paths consistent with the documented architecture.

## Required documentation

Architecture and implementation specifications live under `docs/`. When implementation diverges from a specification, update the specification in the same change rather than leaving contradictory documentation.

## Definition of done

A task is complete only when:

1. The implementation is internally consistent.
2. Relevant tests exist and pass.
3. Configuration and deployment paths are valid.
4. Public API routes are registered and reachable.
5. Dependencies are declared.
6. Documentation reflects the resulting behavior.
7. No known compile-time, import-time, or obvious runtime errors remain in the changed area.
