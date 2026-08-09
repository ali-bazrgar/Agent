from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Mapping


@dataclass(frozen=True, slots=True)
class Principal:
    """Authenticated or trusted caller identity used for data isolation.

    The application must not derive an identity from arbitrary request-body
    fields. Until an authentication adapter is installed, callers use the
    explicit anonymous principal rather than pretending that a client supplied
    user_id is authenticated.
    """

    principal_id: str
    principal_type: str = "user"
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.principal_id.strip():
            raise ValueError("principal_id cannot be blank")
        if not self.principal_type.strip():
            raise ValueError("principal_type cannot be blank")


ANONYMOUS_PRINCIPAL = Principal(
    principal_id="anonymous",
    principal_type="anonymous",
)


@dataclass(frozen=True, slots=True)
class RequestContext:
    """Trusted execution context propagated through the application core."""

    request_id: str
    conversation_id: str
    principal: Principal = ANONYMOUS_PRINCIPAL
    execution_id: str | None = None
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.request_id.strip():
            raise ValueError("request_id cannot be blank")
        if not self.conversation_id.strip():
            raise ValueError("conversation_id cannot be blank")
