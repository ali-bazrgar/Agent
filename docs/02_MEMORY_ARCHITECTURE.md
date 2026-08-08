# Memory Architecture

## Memory as a first-class subsystem

Memory is not a side effect of chat history or vector search. It is a dedicated subsystem responsible for selecting, validating, storing, scoring, and retrieving durable knowledge about the user, the task, the world, and the system's own operations.

## Memory types

The system distinguishes the following durable or semi-durable memory types:

- Working memory: short-lived context for the current execution
- Session memory: conversation state and task state for a user session
- Episodic memory: important events and interactions over time
- Semantic memory: stable factual knowledge
- Procedural memory: reusable workflows and strategies
- User memory: user preferences, goals, projects, interests, skills, and stable knowledge about the user
- Temporal memory: facts whose meaning depends on time or recurrence

## Personal knowledge model

The system maintains a Personal Knowledge Model (PKM) that tracks structured knowledge about the user over time. It may include:

- identity-related non-sensitive application data
- preferences
- goals
- projects
- interests
- skills
- learning state
- stable knowledge
- important events
- temporal facts
- relationships

The PKM must distinguish current state from historical state and must not accept inferred sensitive attributes as facts.

## Explicit vs inferred

Every user-related memory must include a provenance and classification marker:

- `explicit`: directly stated by the user or a trusted source
- `inferred`: derived by the system and never treated as equivalent to an explicit fact

Inferred hypotheses must carry lower confidence and should not be used as authoritative user facts without explicit validation.

## Memory lifecycle

```text
Observation
  ↓
Memory Candidate
  ↓
Classification
  ↓
Validation
  ↓
Scoring
  ↓
Deduplication
  ↓
Consolidation
  ↓
Long-Term Memory
  ↓
Supersession / Expiration / Deletion
```

## Memory record model

Every durable memory should support:

- id
- memory_type
- content
- structured_data
- source_reference
- provenance
- confidence
- importance
- relevance
- created_at
- updated_at
- valid_from
- valid_until
- last_accessed_at
- access_count
- status
- relationships

## Candidate creation

The system should not create a memory for every message. Candidate creation is triggered only when the content is likely to be useful, durable, or actionable.

Examples of useful candidates:

- user preference change
- user goal update
- important event
- knowledge worth retaining
- strong procedural pattern
- repeated failure or learning signal

## Consolidation rules

The subsystem must detect:

- duplicates
- contradictions
- updates
- temporary facts
- high-value stable facts
- low-value noisy information

Consolidation should merge updates into existing memory when appropriate, and it should preserve history rather than overwriting everything blindly.

## Retrieval model

Memory retrieval uses multiple signals:

- semantic relevance
- recency
- importance
- frequency of access
- task relevance
- user relevance
- temporal relevance
- confidence
- provenance reliability

The scoring mechanism must be configurable and testable.

## Expiration and supersession

Temporary facts may expire. Stable facts should not be removed simply because they are old. The subsystem must support:

- expiration at a defined time
- supersession by a newer version
- soft deletion
- explicit deletion

The system must never treat an expired or superseded memory as authoritative without preserving its history.
