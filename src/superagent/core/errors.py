from __future__ import annotations


class SuperAgentError(Exception):
    """Base error for all Super Agent failures."""


class ConfigurationError(SuperAgentError):
    """Raised when configuration is missing or invalid."""


class ValidationError(SuperAgentError):
    """Raised when a domain object fails validation."""


class ProviderError(SuperAgentError):
    """Raised when an external provider fails."""

    def __init__(
        self,
        message: str,
        *,
        provider_name: str | None = None,
        operation: str | None = None,
        status_code: int | None = None,
        retryable: bool | None = None,
    ) -> None:
        super().__init__(message)
        self.provider_name = provider_name
        self.operation = operation
        self.status_code = status_code
        self.retryable = retryable


class PersistenceError(SuperAgentError):
    """Raised when persistence operations fail."""


class DomainError(SuperAgentError):
    """Raised when domain rules are violated."""


class OrchestrationError(SuperAgentError):
    """Raised when orchestration logic cannot proceed."""
