# Super Agent — Project Vision

## Mission

Build a modular, local-first cognitive AI platform around a small local language model while keeping the system substantially more capable through persistent memory, retrieval, tools, learning, and orchestration.

The system must behave less like a chat interface and more like a persistent personal knowledge and reasoning engine.

## Core principles

- The LLM context window is temporary working memory, not the system's memory.
- Persistent knowledge lives in durable storage and retrieval subsystems.
- The application must remain independent from a specific model runtime, model file layout, database engine, vector engine, or context-window size.
- The architecture must support incremental delivery through phased implementation.

## Architectural commitments

- Provider abstraction for LLM, embedding, reranking, and web research.
- A dedicated memory subsystem with layered memory types and explicit/inferred separation.
- A dedicated personal knowledge model for the user over time.
- A dynamic context engine that budgets tokens and selects only the most relevant evidence.
- Adaptive orchestration that prefers the simplest valid execution path.
- Durable knowledge ingestion with rebuildable derived indexes.
- Learning as a first-class subsystem with deterministic scheduling.
- Security, observability, and evaluation built into the architecture from the start.

## Local-first design

The default deployment must be local and self-contained. External services are optional and should be isolated behind interfaces.

## Non-goals for the initial phase

- No distributed microservices.
- No cloud-only deployment.
- No unrestricted autonomous computer control.
- No UI implementation in the architecture phase.
- No production application code before the architecture and phase plan are complete.
