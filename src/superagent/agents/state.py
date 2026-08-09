from __future__ import annotations

import logging
import time
from datetime import datetime, timedelta, timezone
from typing import Any

from superagent.agents.models import AgentExecutionStatus, ExecutionStep
from superagent.models.domain import ExecutionState
from superagent.observability.diagnostics import get_diagnostic_store
from superagent.repositories.ports import ExecutionRepository

logger = logging.getLogger(__name__)


class ExecutionBudgetExceeded(RuntimeError):
    """Raised when an execution exceeds one of its configured safety budgets."""


class AgentStateMachine:
    """Manages explicit deterministic agent state transitions, budgets and persistence."""

    def __init__(
        self,
        execution_id: str,
        request_id: str | None = None,
        execution_repository: ExecutionRepository | None = None,
        *,
        max_model_calls: int = 4,
        max_tool_calls: int = 8,
        max_retries: int = 2,
        max_execution_time_seconds: int = 60,
    ) -> None:
        if max_model_calls < 1 or max_tool_calls < 0 or max_retries < 0 or max_execution_time_seconds < 1:
            raise ValueError("execution budgets must be positive except tool/retry budgets may be zero")
        self.execution_id = execution_id
        self.request_id = request_id
        self.repository = execution_repository
        self.current_status = AgentExecutionStatus.CREATED
        self.steps: list[ExecutionStep] = []
        self.model_calls = 0
        self.tool_calls = 0
        self.retries = 0
        self.max_model_calls = max_model_calls
        self.max_tool_calls = max_tool_calls
        self.max_retries = max_retries
        self.max_execution_time_seconds = max_execution_time_seconds
        self.started_monotonic = time.monotonic()
        self.deadline = datetime.now(timezone.utc) + timedelta(seconds=max_execution_time_seconds)
        self.diagnostics: dict[str, Any] = {
            "execution_budgets": {
                "max_model_calls": max_model_calls,
                "max_tool_calls": max_tool_calls,
                "max_retries": max_retries,
                "max_execution_time_seconds": max_execution_time_seconds,
            }
        }
        self.created_at = datetime.now(timezone.utc)
        self.completed_at: datetime | None = None
        self._diagnostics_store = get_diagnostic_store()
        self._init_persistence()
        self._trace("execution.created")

    def _trace(self, event_type: str, **fields: Any) -> None:
        try:
            self._diagnostics_store.record(event_type, execution_id=self.execution_id, request_id=self.request_id, **fields)
        except Exception as exc:
            logger.debug("Diagnostic tracing failed: %s", exc)

    def ensure_time_remaining(self) -> None:
        elapsed = time.monotonic() - self.started_monotonic
        if elapsed >= self.max_execution_time_seconds:
            self._trace("execution.budget_exceeded", budget="execution_time", elapsed_seconds=elapsed)
            raise ExecutionBudgetExceeded("Maximum execution time exceeded")

    def transition_to(self, new_status: AgentExecutionStatus, details: dict[str, Any] | None = None) -> None:
        self.ensure_time_remaining()
        previous = self.current_status
        logger.info("Execution %s transition: %s -> %s", self.execution_id, previous, new_status)
        self.current_status = new_status
        self.steps.append(ExecutionStep(step_id=f"step-{len(self.steps) + 1}", step_name=new_status.value, status="completed", details=details or {}))
        self._trace("execution.transition", from_status=previous.value, to_status=new_status.value, details=details or {}, step_index=len(self.steps))
        if new_status in (AgentExecutionStatus.COMPLETED, AgentExecutionStatus.FAILED):
            self.completed_at = datetime.now(timezone.utc)
            self._trace("execution.finished", status=new_status.value, model_calls=self.model_calls, tool_calls=self.tool_calls, retries=self.retries)
        self._sync_persistence()

    def increment_model_calls(self) -> None:
        self.ensure_time_remaining()
        if self.model_calls >= self.max_model_calls:
            self._trace("execution.budget_exceeded", budget="model_calls", count=self.model_calls)
            raise ExecutionBudgetExceeded(f"Maximum model calls exceeded: {self.max_model_calls}")
        self.model_calls += 1
        self._trace("execution.model_call", count=self.model_calls)
        self._sync_persistence()

    def increment_tool_calls(self) -> None:
        self.ensure_time_remaining()
        if self.tool_calls >= self.max_tool_calls:
            self._trace("execution.budget_exceeded", budget="tool_calls", count=self.tool_calls)
            raise ExecutionBudgetExceeded(f"Maximum tool calls exceeded: {self.max_tool_calls}")
        self.tool_calls += 1
        self._trace("execution.tool_call", count=self.tool_calls)
        self._sync_persistence()

    def increment_retries(self) -> None:
        self.ensure_time_remaining()
        if self.retries >= self.max_retries:
            self._trace("execution.budget_exceeded", budget="retries", count=self.retries)
            raise ExecutionBudgetExceeded(f"Maximum retries exceeded: {self.max_retries}")
        self.retries += 1
        self._trace("execution.retry", count=self.retries)
        self._sync_persistence()

    def add_diagnostic(self, key: str, value: Any) -> None:
        self.diagnostics[key] = value
        self._trace("execution.diagnostic", key=key, value=value)
        self._sync_persistence()

    def to_domain_state(self) -> ExecutionState:
        return ExecutionState(execution_id=self.execution_id, request_id=self.request_id, status=self.current_status.value, model_calls=self.model_calls, tool_calls=self.tool_calls, retries=self.retries, created_at=self.created_at, completed_at=self.completed_at, metadata={"steps": [s.model_dump(mode="json") for s in self.steps], "diagnostics": self.diagnostics})

    def _init_persistence(self) -> None:
        if self.repository is not None:
            try:
                self.repository.create_execution(self.to_domain_state())
            except Exception as exc:
                logger.warning("Failed to persist initial execution state: %s", exc)

    def _sync_persistence(self) -> None:
        if self.repository is not None:
            try:
                self.repository.update_execution(self.to_domain_state())
            except Exception as exc:
                logger.warning("Failed to update execution state: %s", exc)
