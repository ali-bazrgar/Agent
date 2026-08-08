# Testing Strategy

## Testing as a first-class architectural concern

Every major subsystem must have automated tests before implementation is considered complete. The tests must be model-free where practical so the suite remains deterministic and fast.

## Test layers

- unit tests for domain logic
- component tests for services and repositories
- integration tests for storage and provider adapters
- API tests for request validation and error handling
- end-to-end tests for major workflows
- evaluation tests for retrieval, memory, and learning quality

## Model-free testing

Most tests should use mock providers rather than real GGUF models or live runtimes.

Representative test doubles:

- `MockLLMProvider`
- `MockEmbeddingProvider`
- `MockRerankerProvider`
- `MockWebResearchProvider`

## Evaluation focus

The evaluation subsystem should eventually measure:

- routing accuracy
- retrieval quality
- reranking quality
- memory precision
- memory recall
- context quality
- hallucination rate
- citation correctness
- tool selection
- answer quality
- learning and flashcard quality

## Failure handling tests

The test suite must simulate:

- model server unavailability
- timeout
- malformed content
- invalid documents
- corrupted indexes
- database failure
- web failure
- reranker failure

The system must degrade gracefully under these conditions.
