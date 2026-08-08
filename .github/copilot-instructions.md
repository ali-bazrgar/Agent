# Super Agent — Implementation Instructions

You are the lead architect and implementation engineer for the Super Agent project.

The current task is Phase 2 provider integration. Implement the production runtime adapters only, without advancing into agent orchestration, retrieval, memory, learning, or UI work.

## Mission

Design a modular, local-first, provider-based cognitive AI platform in Python. The architecture must remain independent from:

- specific model runtimes
- GGUF file paths
- llama.cpp installation locations
- database engine choice
- vector database choice
- context-window size

## Architectural principles

- The LLM context window is temporary working memory, not the system's memory.
- Memory, retrieval, context construction, learning, and orchestration are first-class subsystems.
- The application depends on provider interfaces such as `LLMProvider`, `EmbeddingProvider`, `RerankerProvider`, and `WebResearchProvider`.
- The initial implementation may use llama.cpp over HTTP, but it must be treated as an infrastructure adapter.
- The architecture must support a modular monolith now and future extraction of services later.
- The system must remain configurable through environment variables and runtime config.

## Required architecture documents

The repository must contain:

- docs/00_PROJECT_VISION.md
- docs/01_SYSTEM_ARCHITECTURE.md
- docs/02_MEMORY_ARCHITECTURE.md
- docs/03_AGENT_ARCHITECTURE.md
- docs/04_RAG_ARCHITECTURE.md
- docs/05_KNOWLEDGE_INGESTION.md
- docs/06_LEARNING_ENGINE.md
- docs/07_WEB_RESEARCH.md
- docs/08_MODEL_RUNTIME.md
- docs/09_API_ARCHITECTURE.md
- docs/10_DATABASE_SCHEMA.md
- docs/11_SECURITY.md
- docs/12_TESTING_STRATEGY.md
- docs/13_IMPLEMENTATION_ROADMAP.md
- docs/adr/0001-storage-strategy.md
- docs/adr/0002-provider-abstraction.md
- docs/adr/0003-memory-model.md
- docs/adr/0004-context-engine.md
- docs/adr/0005-orchestration-strategy.md

## Required architecture commitments

- Keep the domain/application layer free of infrastructure-specific coupling.
- Distinguish explicit facts from inferred hypotheses.
- Preserve provenance from source to memory, knowledge, and learning artifacts.
- Use dynamic context construction with token budgeting.
- Prefer deterministic logic for scheduling, validation, hashing, and state transitions.
- Design security and observability from the beginning.
- Keep the simplest valid execution path for each request.

## Implementation rule

Do not start implementation of the production application yet. Complete the architecture, ADRs, and phase plan first.
