from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any

from superagent.agents.models import AgentExecutionStatus, ExecutionStep
from superagent.models.domain import ExecutionState
from superagent.repositories.ports import ExecutionRepository

logger = logging.getLogger(__name__)


class AgentStateMachine:
    """Manages explicit deterministic agent state transitions and persistence."""

    def __init__(
        self,
        execution_id: str,
        request_id: str | None = None,
        execution_repository: ExecutionRepository | None = None,
    ) -> None:
        self.execution_id = execution_id
        self.request_id = request_id
        self.repository = execution_repository
        self.current_status = AgentExecutionStatus.CREATED
        self.steps: list[ExecutionStep] = []
        self.model_calls = 0
        self.tool_calls = 0
        self.retries = 0
        self.diagnostics: dict[str, Any] = {}
        self.created_at = datetime.now(timezone.utc)
        self.completed_at: datetime | None = None

        self._init_persistence()

    def transition_to(
        self,
        new_status: AgentExecutionStatus,
        details: dict[str, Any] | None = None,
    ) -> None:
        logger.info(f"Execution {self.execution_id} transition: {self.current_status} -> {new_status}")
        self.current_status = new_status
        step = ExecutionStep(
            step_id=f"step-{len(self.steps) + 1}",
            step_name=new_status.value,
            status="completed",
            details=details or {},
        )
        self.steps.append(step)

        if new_status in (AgentExecutionStatus.COMPLETED, AgentExecutionStatus.FAILED):
            self.completed_at = datetime.now(timezone.utc)

        self._sync_persistence()

    def increment_model_calls(self) -> None:
        self.model_calls += 1
        self._sync_persistence()

    def increment_retries(self) -> None:
        self.retries += 1
        self._sync_persistence()

    def add_diagnostic(self, key: str, value: Any) -> None:
        self.diagnostics[key] = value

    def to_domain_state(self) -> ExecutionState:
        return ExecutionState(
            execution_id=self.execution_id,
            request_id=self.request_id,
            status=self.current_status.value,
            model_calls=self.model_calls,
            tool_calls=self.tool_calls,
            retries=self.retries,
            created_at=self.created_at,
            completed_at=self.completed_at,
            metadata={
                "steps": [s.model_dump(mode="json") for s in self.steps],
                "diagnostics": self.diagnostics,
            },
        )

    def _init_persistence(self) -> None:
        if self.repository is not None:
            try:
                self.repository.create_execution(self.to_domain_state())
            except Exception as exc:
                logger.warning(f"Failed to persist initial execution state: {exc}")

    def _sync_persistence(self) -> None:
        if self.repository is not None:
            try:
                self.repository.update_execution(self.to_domain_state())
            except Exception as exc:
                logger.warning(f"Failed to update execution state: {exc}")
