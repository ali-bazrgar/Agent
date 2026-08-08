from __future__ import annotations

import concurrent.futures
import logging
import re
import time
from typing import Sequence

from superagent.tools.models import ToolCall, ToolExecutionContext, ToolExecutionStatus, ToolResult
from superagent.tools.ports import ToolExecutorPort, ToolRegistryPort

logger = logging.getLogger(__name__)


class ToolExecutor(ToolExecutorPort):
    """Executor with per-execution call limits, timeouts, isolation and secret scrubbing."""

    SECRET_PATTERNS = [
        re.compile(r"(?i)(api[_-]?key|secret|password|token|auth|bearer)\s*[:=]\s*['\"]?([a-zA-Z0-9_\-.]{8,})['\"]?"),
        re.compile(r"sk-[a-zA-Z0-9]{20,}"),
        re.compile(r"AIzaSy[a-zA-Z0-9_-]{33}"),
    ]

    def __init__(self, registry: ToolRegistryPort, default_timeout_seconds: float = 10.0, max_workers: int = 4, max_calls_per_execution: int = 8) -> None:
        self.registry = registry
        self.default_timeout_seconds = default_timeout_seconds
        self.max_calls_per_execution = max(1, max_calls_per_execution)
        self.thread_pool = concurrent.futures.ThreadPoolExecutor(max_workers=max_workers)

    def execute_tool(self, call: ToolCall, context: ToolExecutionContext | None = None) -> ToolResult:
        context = context or ToolExecutionContext()
        start_time = time.perf_counter()
        call_count = int(context.metadata.get("tool_call_count", 0))
        limit = int(context.metadata.get("max_tool_calls", self.max_calls_per_execution))
        if call_count >= max(1, limit):
            return ToolResult(tool_call_id=call.tool_call_id, tool_name=call.tool_name, status=ToolExecutionStatus.ERROR, error=f"Maximum tool calls ({limit}) exceeded.")
        context.metadata["tool_call_count"] = call_count + 1

        provider = self.registry.get(call.tool_name)
        if provider is None:
            return ToolResult(tool_call_id=call.tool_call_id, tool_name=call.tool_name, status=ToolExecutionStatus.ERROR, error=f"Tool '{call.tool_name}' not found or is disabled in registry.", execution_duration_ms=self._elapsed_ms(start_time))
        definition = provider.definition
        if not definition.enabled:
            return ToolResult(tool_call_id=call.tool_call_id, tool_name=call.tool_name, status=ToolExecutionStatus.DISABLED, error=f"Tool '{call.tool_name}' is currently disabled.", execution_duration_ms=self._elapsed_ms(start_time))
        timeout = context.timeout_seconds or definition.timeout_seconds or self.default_timeout_seconds
        try:
            future = self.thread_pool.submit(provider.execute, call, context)
            result = future.result(timeout=timeout)
            result.execution_duration_ms = self._elapsed_ms(start_time)
            return self._scrub_result(result)
        except concurrent.futures.TimeoutError:
            return ToolResult(tool_call_id=call.tool_call_id, tool_name=call.tool_name, status=ToolExecutionStatus.TIMEOUT, error=f"Tool execution timed out after {timeout} seconds.", execution_duration_ms=self._elapsed_ms(start_time))
        except Exception as exc:
            logger.exception("Tool '%s' failed", call.tool_name)
            return ToolResult(tool_call_id=call.tool_call_id, tool_name=call.tool_name, status=ToolExecutionStatus.ERROR, error=self.scrub_text(str(exc)), execution_duration_ms=self._elapsed_ms(start_time))

    def execute_tools(self, calls: Sequence[ToolCall], context: ToolExecutionContext | None = None) -> list[ToolResult]:
        return [self.execute_tool(call, context) for call in calls]

    def close(self) -> None:
        self.thread_pool.shutdown(wait=False, cancel_futures=True)

    @classmethod
    def scrub_text(cls, text: str) -> str:
        sanitized = text or ""
        for pattern in cls.SECRET_PATTERNS:
            sanitized = pattern.sub("[REDACTED_SECRET]", sanitized)
        return sanitized

    def _scrub_result(self, result: ToolResult) -> ToolResult:
        if result.error:
            result.error = self.scrub_text(result.error)
        if isinstance(result.output, str):
            result.output = self.scrub_text(result.output)
        elif isinstance(result.output, dict):
            result.output = {key: self.scrub_text(value) if isinstance(value, str) else value for key, value in result.output.items()}
        return result

    @staticmethod
    def _elapsed_ms(start_time: float) -> float:
        return round((time.perf_counter() - start_time) * 1000.0, 2)
