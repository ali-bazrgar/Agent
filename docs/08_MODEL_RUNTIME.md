# Model Runtime Architecture

## Provider-based model runtime

All model inference is abstracted behind stable provider interfaces. The application layer never needs to know about GGUF files, executable paths, model-specific flags, or backend-specific runtime details.

## Provider interfaces

The runtime exposes:

- `LLMProvider` for generation and structured output
- `EmbeddingProvider` for single and batch embedding
- `RerankerProvider` for scoring and reranking
- `WebResearchProvider` for search and retrieval of web evidence

## Runtime adaptation

The initial implementation may use llama.cpp through HTTP servers, but those services are adapters. The domain/application layer only sees provider interfaces and runtime configuration.

## Configuration-driven runtime

The runtime configuration must include:

- base URLs or endpoint addresses
- model identifier or alias
- capability profile
- timeout values
- retry policy
- token budget
- feature flags

The application should not hard-code model paths or ports.

## Capability detection

Provider implementations expose capabilities such as:

- streaming
- embedding
- structured output
- tool calling
- context size
- model metadata

The context engine uses capability metadata to allocate token budgets correctly.

## Failure handling

Model runtime failures must surface as structured provider errors. The application should:

- preserve execution state
- expose health status
- retry where appropriate
- fail gracefully

## Local provider configuration

The Phase 2 implementation uses the provider interfaces with concrete HTTP adapters for llama.cpp. Configuration is environment-driven and must include:

- `LLM_BASE_URL`
- `EMBEDDING_BASE_URL`
- `RERANKER_BASE_URL`
- optional model identifiers
- optional API key/auth configuration
- timeout and retry settings

The application keeps llama.cpp behind the provider boundary and does not depend on executable paths, GGUF files, or Windows-specific locations.

## Future providers

The architecture supports future providers such as:

- llama.cpp HTTP adapter
- OpenAI-compatible adapter
- Ollama adapter
- another local backend

without changing the business logic.
