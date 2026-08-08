# Phase 7: Web Research Specification

## Overview
The Web Research subsystem orchestrates web search and content fetching into structured, ephemeral research evidence that is integrated into the Context Engine for LLM grounding.

## Architecture
- **Web Research Provider (`WebResearchProvider`)**: Abstract port defining `search(request)` returning normalized `WebResearchResponse` items (title, url, snippet, source, published_at).
- **Default Provider (`DefaultWebSearchProvider`)**: Lightweight implementation supporting custom search endpoints and graceful fallbacks when unconfigured.
- **Research Pipeline (`ResearchPipeline`)**: Orchestrates multi-step research:
  1. Executes web search with the query.
  2. Selects top search results and generates snippet evidence.
  3. Fetches top webpage contents via `WebFetchTool` with SSRF protection and HTML text extraction.
  4. Produces ephemeral `ResearchEvidence` objects.

## Ephemeral vs Persistent Separation
- Web research evidence is treated as ephemeral context and is passed into the Context Engine (`ContextItemKind.RESEARCH_EVIDENCE`).
- Web articles are **NOT** automatically persisted as permanent user memories, preserving memory integrity for user-authored preferences and interactions.

## Provenance & Verification
- Research evidence preserves source URLs and titles in its provenance metadata.
- Agent Verifier and Critic evaluate web-backed claims against the retrieved research evidence to ensure factual accuracy and detect unsupported assertions.
