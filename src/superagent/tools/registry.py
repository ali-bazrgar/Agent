from __future__ import annotations

import logging

from superagent.tools.models import ToolDefinition
from superagent.tools.ports import ToolProvider, ToolRegistryPort

logger = logging.getLogger(__name__)


class ToolRegistry(ToolRegistryPort):
    """Deterministic, in-memory tool registry."""

    def __init__(self) -> None:
        self._tools: dict[str, ToolProvider] = {}

    def register(self, tool: ToolProvider) -> None:
        name = tool.definition.name.strip().lower()
        if name in self._tools:
            logger.info(f"Overwriting existing tool registration for '{name}'.")
        self._tools[name] = tool

    def unregister(self, tool_name: str) -> None:
        name = tool_name.strip().lower()
        if name in self._tools:
            del self._tools[name]

    def get(self, tool_name: str) -> ToolProvider | None:
        name = tool_name.strip().lower()
        return self._tools.get(name)

    def list_tools(self) -> list[ToolDefinition]:
        # Return sorted by name for deterministic order
        sorted_keys = sorted(self._tools.keys())
        return [self._tools[k].definition for k in sorted_keys if self._tools[k].definition.enabled]

    def has(self, tool_name: str) -> bool:
        name = tool_name.strip().lower()
        return name in self._tools and self._tools[name].definition.enabled
