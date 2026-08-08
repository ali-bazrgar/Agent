from __future__ import annotations

import concurrent.futures
import logging
import re
import time
from typing import Sequence

from superagent.tools.models import (
    ToolCall,
    ToolExecutionContext,
    ToolExecutionStatus,
    ToolResult,
)
from superagent.tools.ports import ToolExecutorPort, ToolRegistryPort

logger = logging.getLogger(__name__)


class ToolExecutor(ToolExecutorPort):
    """Executor managing bounded, isolated, and safe execution of tools."""

    SECRET_PATTERNS = [
        re.compile(r"(?i)(api[_-]?key|secret|password|token|auth|bearer)\s*[:=]\s*['\"]?([a-zA-Z0-9_\-\.]{8,})['\"]?"),
        re.compile(r"sk-[a-zA-Z0-9]{20,}"),
        re.compile(r"AIzaSy[a-zA-Z0-9_\-]{33}"),
    ]

    def __init__(
        self,
        registry: ToolRegistryPort,
        default_timeout_seconds: float = 10.0,
        max_workers: int = 4,
    ) -> None:
        self.registry = registry
        self.default_timeout_seconds = default_timeout_seconds
        self.thread_pool = concurrent.futures.ThreadPoolExecutor(max_workers=max_workers)

    def execute_tool(
        self,
        call: ToolCall,
        context: ToolExecutionContext | None = None,
    ) -> ToolResult:
        context = context or ToolExecutionContext()
        start_time = time.perf_counter()

        tool_provider = self.registry.get(call.tool_name)
        if tool_provider is None:
            return ToolResult(
                tool_call_id=call.tool_call_id,
                tool_name=call.tool_name,
                status=ToolExecutionStatus.ERROR,
                error=f"Tool '{call.tool_name}' not found or is disabled in registry.",
                execution_duration_ms=self._elapsed_ms(start_time),
            )

        definition = tool_provider.definition
        if not definition.enabled:
            return ToolResult(
                tool_call_id=call.tool_call_id,
                tool_name=call.tool_name,
                status=ToolExecutionStatus.DISABLED,
                error=f"Tool '{call.tool_name}' is currently disabled.",
                execution_duration_ms=self._elapsed_ms(start_time),
            )

        timeout = context.timeout_seconds or definition.timeout_seconds or self.default_timeout_seconds

        try:
            future = self.thread_pool.submit(tool_provider.execute, call, context)
            result = future.result(timeout=timeout)
            duration = self._elapsed_ms(start_time)
            result.execution_duration_ms = duration
            return self._scrub_result(result)

        except concurrent.futures.TimeoutError:
            duration = self._elapsed_ms(start_time)
            logger.warning(f"Tool '{call.tool_name}' timed out after {timeout} seconds.")
            return ToolResult(
                tool_call_id=call.tool_call_id,
                tool_name=call.tool_name,
                status=ToolExecutionStatus.TIMEOUT,
                error=f"Tool execution timed out after {timeout} seconds.",
                execution_duration_ms=duration,
            )

        except Exception as exc:
            duration = self._elapsed_ms(start_time)
            logger.exception(f"Tool '{call.tool_name}' failed with exception: {exc}")
            return ToolResult(
                tool_call_id=call.tool_call_id,
                tool_name=call.tool_name,
                status=ToolExecutionStatus.ERROR,
                error=self.scrub_text(str(exc)),
                execution_duration_ms=duration,
            )

    def execute_tools(
        self,
        calls: Sequence[ToolCall],
        context: ToolExecutionContext | None = None,
    ) -> list[ToolResult]:
        return [self.execute_tool(call, context) for call in calls]

    @classmethod
    def scrub_text(cls, text: str) -> str:
        if not text:
            return text
        sanitized = text
        for pattern in cls.SECRET_PATTERNS:
            sanitized = pattern.sub("[REDACTED_SECRET]", sanitized)
        return sanitized

    def _scrub_result(self, result: ToolResult) -> ToolResult:
        if result.error:
            result.error = self.scrub_text(result.error)
        if isinstance(result.output, str):
            result.output = self.scrub_text(result.output)
        elif isinstance(result.output, dict):
            result.output = {
                k: self.scrub_text(v) if isinstance(v, str) else v
                for k, v in result.output.items()
            }
        return result

    @staticmethod
    def _elapsed_ms(start_time: float) -> float:
        return round((time.perf_counter() - start_time) * 1000.0, 2)
