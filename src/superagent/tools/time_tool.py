from __future__ import annotations

from datetime import datetime, timezone
import zoneinfo
from typing import Any

from superagent.tools.models import (
    RiskLevel,
    ToolCall,
    ToolDefinition,
    ToolExecutionContext,
    ToolExecutionStatus,
    ToolResult,
)
from superagent.tools.ports import ToolProvider


class TimeTool(ToolProvider):
    """Tool providing current date and time for requested timezones."""

    @property
    def definition(self) -> ToolDefinition:
        return ToolDefinition(
            name="current_time",
            description="Returns current date, time, and UTC offset for a requested timezone.",
            input_schema={
                "type": "object",
                "properties": {
                    "timezone": {
                        "type": "string",
                        "description": "IANA timezone identifier (e.g., 'UTC', 'America/New_York', 'Europe/London'). Defaults to 'UTC'.",
                        "default": "UTC",
                    }
                },
            },
            output_schema={
                "type": "object",
                "properties": {
                    "timezone": {"type": "string"},
                    "datetime": {"type": "string"},
                    "utc_offset": {"type": "string"},
                },
            },
            requires_network=False,
            risk_level=RiskLevel.LOW,
            timeout_seconds=1.0,
            enabled=True,
        )

    def execute(
        self,
        call: ToolCall,
        context: ToolExecutionContext | None = None,
    ) -> ToolResult:
        tz_name = call.arguments.get("timezone", "UTC")
        if not isinstance(tz_name, str) or not tz_name.strip():
            tz_name = "UTC"

        tz_clean = tz_name.strip()

        try:
            if tz_clean.upper() == "UTC":
                tz = timezone.utc
            else:
                tz = zoneinfo.ZoneInfo(tz_clean)

            now = datetime.now(tz)
            utc_offset = now.strftime("%z")
            if utc_offset:
                utc_offset = f"{utc_offset[:3]}:{utc_offset[3:]}"

            return ToolResult(
                tool_call_id=call.tool_call_id,
                tool_name="current_time",
                status=ToolExecutionStatus.SUCCESS,
                output={
                    "timezone": tz_clean,
                    "datetime": now.isoformat(),
                    "utc_offset": utc_offset or "+00:00",
                },
            )
        except zoneinfo.ZoneInfoNotFoundError:
            return ToolResult(
                tool_call_id=call.tool_call_id,
                tool_name="current_time",
                status=ToolExecutionStatus.ERROR,
                error=f"Invalid or unknown timezone identifier: '{tz_clean}'. Please use a valid IANA timezone (e.g. 'UTC', 'America/New_York').",
            )
        except Exception as exc:
            return ToolResult(
                tool_call_id=call.tool_call_id,
                tool_name="current_time",
                status=ToolExecutionStatus.ERROR,
                error=f"Failed to fetch time for timezone '{tz_clean}': {exc}",
            )
