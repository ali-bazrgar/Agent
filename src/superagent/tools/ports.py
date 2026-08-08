from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Sequence

from superagent.tools.models import (
    ToolCall,
    ToolDefinition,
    ToolExecutionContext,
    ToolResult,
)


class ToolProvider(ABC):
    """Interface for a concrete tool capability."""

    @property
    @abstractmethod
    def definition(self) -> ToolDefinition: ...

    @abstractmethod
    def execute(
        self,
        call: ToolCall,
        context: ToolExecutionContext | None = None,
    ) -> ToolResult: ...


class ToolRegistryPort(ABC):
    """Interface for tool registration and lookup."""

    @abstractmethod
    def register(self, tool: ToolProvider) -> None: ...

    @abstractmethod
    def unregister(self, tool_name: str) -> None: ...

    @abstractmethod
    def get(self, tool_name: str) -> ToolProvider | None: ...

    @abstractmethod
    def list_tools(self) -> list[ToolDefinition]: ...

    @abstractmethod
    def has(self, tool_name: str) -> bool: ...


class ToolExecutorPort(ABC):
    """Interface for safe execution of tool calls."""

    @abstractmethod
    def execute_tool(
        self,
        call: ToolCall,
        context: ToolExecutionContext | None = None,
    ) -> ToolResult: ...

    @abstractmethod
    def execute_tools(
        self,
        calls: Sequence[ToolCall],
        context: ToolExecutionContext | None = None,
    ) -> list[ToolResult]: ...
