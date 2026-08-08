# API Architecture

## Transport layer

The API layer is responsible for transport, validation, authentication boundaries, and serialization. It should not contain business logic.

## Versioning

The API should be versioned from the start, for example:

- `/api/v1/chat`
- `/api/v1/documents`
- `/api/v1/knowledge`
- `/api/v1/memory/search`
- `/api/v1/research`
- `/api/v1/flashcards`
- `/api/v1/reviews`
- `/api/v1/health`

## Contracts

Requests and responses should use Pydantic models. The API should return structured errors with request ids and correlation metadata.

## Dependency direction

The API depends on application services. The application services depend on domain abstractions and repository interfaces.

## Streaming and async behavior

The API should support streaming responses where appropriate, but streaming must not bypass persistence, observability, or memory recording.

## Authentication and authorization

Authentication and authorization are part of the API architecture even if the initial implementation uses a simple local or placeholder policy. The design must support later user isolation and tenant-aware access.
