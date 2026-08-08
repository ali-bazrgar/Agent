# Agent Architecture

## Adaptive orchestration

The orchestrator is not a fixed chain of prompts. It evaluates each request and chooses the simplest valid execution path.

## Routing policy

The router classifies each request by:

- intent type
- complexity
- need for memory
- need for retrieval
- need for tools
- need for web research
- need for deeper reasoning

## Execution patterns

### Simple request

```text
Router → LLM
```

### Knowledge request

```text
Router → Retrieval → Context Engine → LLM
```

### Complex request

```text
Router → Planner → Retrieval/Tools → Verification → LLM
```

### Research request

```text
Router → Web Research → Evidence Processing → Synthesis → optional storage
```

### Learning request

```text
Router → Knowledge/Memory → Learning Engine → Review/Flashcards → storage
```

## Logical roles

The system may use the following logical roles, but they are not required to be separate models:

- Router
- Planner
- Retriever
- Researcher
- Reasoner
- Critic
- Verifier
- Synthesizer
- Memory Manager
- Knowledge Manager
- Learning Agent
- Tool Executor
- Context Manager

## Execution state

Every execution must have explicit serializable state:

- execution_id
- request
- plan
- current_step
- retrieval_results
- tool_results
- critique
- verification
- final_response
- status
- budgets_used

## Budgets

Every execution must enforce budgets:

- max_model_calls
- max_tool_calls
- max_retries
- max_execution_time
- max_context_tokens

The orchestrator stops when any budget is exhausted.

## Deterministic vs model-driven steps

Prefer deterministic logic for:

- dates and time handling
- token budgeting
- hashing and deduplication
- permissions and validation
- retry limits
- state transitions
- FSRS scheduling

Use the LLM for semantic interpretation, extraction, synthesis, and reasoning.

## Reflection and verification

The system should support structured critique and verification without exposing hidden chain-of-thought. Verification should produce evidence-backed outcomes such as supported, contradicted, or insufficient evidence.

## Safety guardrails

- The orchestrator must avoid infinite loops.
- Tools must be permissioned and schema-validated.
- The LLM must never directly execute arbitrary shell commands.
- The orchestrator must preserve execution state even on provider failure.

---

# 15. Final Response Pipeline

The preferred conceptual pipeline is:

```text
USER
 ↓
ROUTER
 ↓
MEMORY + KNOWLEDGE RETRIEVAL
 ↓
PLANNER
 ↓
TOOLS / WEB / RETRIEVAL
 ↓
CONTEXT ENGINE
 ↓
LLM
 ↓
CRITIC
 ↓
VERIFIER
 ↓
REPAIR IF NEEDED
 ↓
FINAL RESPONSE
 ↓
MEMORY EXTRACTION
 ↓
PERSISTENCE
```

The Router may bypass unnecessary stages.

---

# 16. Agent Architecture Principle

The system should maximize intelligence per model token.

Do not increase intelligence by blindly increasing prompt size.

Use:

```text
better information
+
better selection
+
better planning
+
better verification
```

rather than:

```text
more tokens
```
