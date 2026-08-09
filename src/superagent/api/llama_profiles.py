from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Literal

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from superagent.api.chat import get_container
from superagent.application.container import AppContainer
from superagent.config.settings import get_settings
from superagent.llm.llama_cpp_config import LlamaCppRuntimeOptions

router = APIRouter(prefix="/config/llama", tags=["llama.cpp configuration"])


class LlamaProfile(BaseModel):
    role: Literal["llm", "embedding", "reranker"]
    executable_path: str = ""
    model_path: str = ""
    mmproj_path: str = ""
    draft_model_path: str = ""
    options: LlamaCppRuntimeOptions = Field(default_factory=LlamaCppRuntimeOptions)


def _profile_path() -> Path:
    settings = get_settings()
    settings.storage_path_resolved.mkdir(parents=True, exist_ok=True)
    return settings.storage_path_resolved / "llama_profiles.json"


def _load() -> dict[str, Any]:
    path = _profile_path()
    if not path.exists():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else {}
    except (OSError, json.JSONDecodeError) as exc:
        raise HTTPException(status_code=500, detail=f"Cannot read llama.cpp profiles: {exc}") from exc


def _save(data: dict[str, Any]) -> None:
    path = _profile_path()
    tmp = path.with_suffix(".tmp")
    try:
        tmp.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
        tmp.replace(path)
    except OSError as exc:
        raise HTTPException(status_code=500, detail=f"Cannot save llama.cpp profiles: {exc}") from exc


@router.get("/profiles")
def list_profiles() -> dict[str, Any]:
    return {"profiles": _load(), "path": str(_profile_path())}


@router.get("/profiles/{role}")
def get_profile(role: Literal["llm", "embedding", "reranker"]) -> dict[str, Any]:
    return {"profile": _load().get(role, LlamaProfile(role=role).model_dump(mode="json"))}


@router.put("/profiles/{role}")
def put_profile(role: Literal["llm", "embedding", "reranker"], payload: LlamaProfile) -> dict[str, Any]:
    if payload.role != role:
        raise HTTPException(status_code=422, detail="profile role does not match URL")
    data = _load()
    data[role] = payload.model_dump(mode="json")
    _save(data)
    return {"ok": True, "profile": data[role], "path": str(_profile_path())}


@router.post("/command")
def render_command(payload: LlamaProfile) -> dict[str, Any]:
    if not payload.executable_path.strip():
        raise HTTPException(status_code=422, detail="executable_path is required")
    model_path = payload.model_path.strip() or None
    command = payload.options.command(payload.executable_path.strip(), model_path=model_path)
    if payload.mmproj_path.strip():
        command.extend(["--mmproj", payload.mmproj_path.strip()])
    if payload.draft_model_path.strip():
        command.extend(["--model-draft", payload.draft_model_path.strip()])
    return {"command": command, "shell_command": " ".join(_quote(item) for item in command), "role": payload.role}


def _quote(value: str) -> str:
    if value and all(ch.isalnum() or ch in "._:/\\-=" for ch in value):
        return value
    return '"' + value.replace('"', '\\"') + '"'
