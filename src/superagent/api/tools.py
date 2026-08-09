from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from superagent.api.chat import get_container
from superagent.application.container import AppContainer

router = APIRouter(tags=["tools"])


@router.get("/tools")
def list_tools(container: AppContainer = Depends(get_container)) -> list[dict[str, object]]:
    """Expose the exact tool registry used by the active chat agent."""
    return [tool.model_dump(mode="json") for tool in container.tool_registry.list_tools()]


@router.get("/tools/{tool_name}")
def get_tool(tool_name: str, container: AppContainer = Depends(get_container)) -> dict[str, object]:
    tool = container.tool_registry.get(tool_name)
    if tool is None:
        raise HTTPException(status_code=404, detail=f"Tool '{tool_name}' not found.")
    return tool.definition.model_dump(mode="json")
