# Phase 11 — Configuration Architecture

## Overview
SuperAgent features a centralized configuration engine covering LLM infrastructure, Embeddings, Rerankers, Web Research, Agent parameters, Context budgets, Learning settings, Database paths, and Observability.

## Categories & Parameters
- **LLM**: Provider type, base URL, model ID, API key, timeout, context window, temperature, max tokens, top_p, top_k, repeat_penalty, streaming.
- **Embeddings**: Provider, base URL, model ID, dimensions, batch size.
- **Reranker**: Provider, base URL, model ID, top_n, enabled state.
- **Web Research**: Search provider, timeout, max pages, max steps.
- **Agent**: Max iterations, max revisions, max tool calls, confidence thresholds.
- **Context**: Window size, reserved output, budgets for system, memory, knowledge, conversation.
- **Learning**: Enabled state, daily review limit, new cards per day, scheduler config.
- **Database & Storage**: Database path, storage path, backup policy.
- **Observability**: Log level, structured logging, execution trace retention.

## Import / Export
- Non-secret configuration export JSON.
- Secure import validation with preview and rollback mechanisms.
