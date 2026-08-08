# Agent Orchestration Specification (Phase 6)

## Overview
Phase 6 introduces a deterministic, stateful agent execution system that coordinates routing, planning, memory retrieval, knowledge retrieval, context construction, LLM generation, critic evaluation, claim verification, bounded self-correction revision loops, and interaction memory lifecycle processing.

## Architecture & Components

### 1. Agent Domain Models (`src/superagent/agents/models.py`)
- **`AgentRequest`**: Holds request query, conversation ID, system instructions, and execution config.
- **`AgentResponse`**: Structured output containing answer, status, iterations, feature usages (`used_retrieval`, `used_memory`, `used_critic`, `used_verifier`), provenance, and diagnostics.
- **`AgentRoute`**: Execution route (`DIRECT`, `MEMORY`, `RETRIEVAL`, `RETRIEVAL_AND_MEMORY`, `RESEARCH_READY`).
- **`AgentExecutionStatus`**: Explicit execution states (`CREATED`, `ROUTING`, `PLANNING`, `RETRIEVING`, `CONTEXT_BUILDING`, `GENERATING`, `CRITIQUING`, `VERIFYING`, `REVISING`, `MEMORY_PROCESSING`, `COMPLETED`, `FAILED`).
- **`ExecutionPlan`**: Defines bounded plan, active steps, max iterations, and required subsystems.
- **`CritiqueResult`**: Captures factuality, relevance, completeness scores, issues, and required revisions.
- **`VerificationResult`**: Verifies factual claims against retrieved evidence (`SUPPORTED`, `UNSUPPORTED`, `CONTRADICTED`, `UNKNOWN`).

### 2. State Machine & Persistence (`src/superagent/agents/state.py`)
- `AgentStateMachine` handles deterministic transitions between execution states.
- Persists step history, model call counters, retries, and diagnostics to `ExecutionRepository`.

### 3. Agent Router (`src/superagent/agents/router.py`)
- Evaluates query patterns and conversation context to select the execution route.
- Supports manual override via execution config.

### 4. Agent Planner (`src/superagent/agents/planner.py`)
- Constructs an `ExecutionPlan` specifying active stages and iteration limits (`max_iterations`, default 2).

### 5. Orchestrator Engine (`src/superagent/agents/orchestrator.py`)
- Central engine executing the full pipeline:
  `Router -> Planner -> Memory/Knowledge Retrieval -> ContextEngine -> LLM -> Critic -> Verifier -> Revision Loop -> Memory Lifecycle -> Execution Persistence`

### 6. Critic & Verifier (`src/superagent/agents/critic.py`, `src/superagent/agents/verifier.py`)
- Critic evaluates output quality, completeness, and hallucination risks.
- Verifier checks assertions against context provenance.

### 7. API Endpoints (`src/superagent/api/chat.py`)
- `POST /api/v1/chat`: Main execution entrypoint.
- `GET /api/v1/executions/{execution_id}`: Retrieves execution state and diagnostics.
