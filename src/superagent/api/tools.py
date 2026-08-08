from __future__ import annotations

from fastapi import APIRouter, HTTPException

from superagent.application.container import AppContainer

router = APIRouter(tags=["tools"])


@router.get("/tools")
def list_tools():
    container = AppContainer()
    tools = container.tool_registry.list_tools()
    return [t.model_dump(mode="json") for t in tools]


@router.get("/tools/{tool_name}")
def get_tool(tool_name: str):
    container = AppContainer()
    tool = container.tool_registry.get(tool_name)
    if tool is None:
        raise HTTPException(status_code=404, detail=f"Tool '{tool_name}' not found.")
    return tool.definition.model_dump(mode="json")
