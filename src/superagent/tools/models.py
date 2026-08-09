from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class RiskLevel(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class ToolExecutionStatus(str, Enum):
    SUCCESS = "success"
    ERROR = "error"
    TIMEOUT = "timeout"
    DISABLED = "disabled"
    INVALID_ARGUMENTS = "invalid_arguments"
    SECURITY_REJECTED = "security_rejected"


class ToolParameter(BaseModel):
    name: str = Field(min_length=1)
    type: str = Field(default="string")
    description: str = Field(default="")
    required: bool = True
    default: Any = None


class ToolDefinition(BaseModel):
    name: str = Field(min_length=1)
    description: str = Field(default="")
    input_schema: dict[str, Any] = Field(default_factory=dict)
    output_schema: dict[str, Any] = Field(default_factory=dict)
    requires_network: bool = False
    risk_level: RiskLevel = RiskLevel.LOW
    timeout_seconds: float = Field(default=10.0, ge=0.1, le=120.0)
    enabled: bool = True


class ToolCall(BaseModel):
    tool_call_id: str = Field(min_length=1)
    tool_name: str = Field(min_length=1)
    arguments: dict[str, Any] = Field(default_factory=dict)


class ToolExecutionContext(BaseModel):
    execution_id: str | None = None
    user_id: str | None = None
    principal_id: str | None = None
    conversation_id: str | None = None
    project_id: str | None = None
    timeout_seconds: float | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class ToolResult(BaseModel):
    tool_call_id: str = Field(min_length=1)
    tool_name: str = Field(min_length=1)
    status: ToolExecutionStatus = ToolExecutionStatus.SUCCESS
    output: Any = None
    error: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)
    execution_duration_ms: float = Field(default=0.0, ge=0.0)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
