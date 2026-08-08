# Learning Engine

## Learning as a first-class subsystem

The learning engine turns knowledge into durable study material and review state. It is responsible for creating learning objects, scheduling reviews, and tracking retention without letting the LLM decide scheduling directly.

## Learning objects

The learning subsystem should support:

- Concept
- KnowledgeGap
- Flashcard
- QuestionAnswerCard
- ClozeCard
- ExplanationCard
- Review
- LearningSession
- MasteryState

## Content generation

The LLM may generate learning content from:

- documents
- knowledge
- conversations
- web research
- user mistakes
- detected knowledge gaps

The learning engine validates and stores the generated content.

## Review scheduling

The learning engine uses a scheduling interface rather than letting the LLM invent dates. The initial implementation may use an FSRS-based scheduler, but the scheduling component must be replaceable.

## FSRS design

The learning subsystem should support:

- difficulty
- stability
- retrievability
- review history
- retention estimation
- deterministic review scheduling

## Learning state

Learning state is stored independently from the model. This includes:

- card state
- review history
- mastery estimates
- due dates
- user progress
- knowledge gaps

## Feedback loop

```text
Knowledge / Memory
  ↓
Concept extraction
  ↓
Flashcard generation
  ↓
Review
  ↓
Performance data
  ↓
Knowledge gap detection
  ↓
Targeted learning
  ↓
Review
```

## Provenance

All learning content retains provenance to the original source document, chunk, knowledge entry, or memory item.
