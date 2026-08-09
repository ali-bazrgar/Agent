from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Literal

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from superagent.config.settings import get_settings
from superagent.llm.llama_cpp_config import LlamaCppRuntimeOptions

router = APIRouter(prefix="/config/llama", tags=["llama.cpp configuration"])

_DEFAULT_PORTS: dict[str, int] = {"llm": 8080, "embedding": 8081, "reranker": 8082}


class LlamaProfile(BaseModel):
    role: Literal["llm", "embedding", "reranker"]
    executable_path: str = ""
    model_path: str = ""
    mmproj_path: str = ""
    draft_model_path: str = ""
    port: int | None = Field(default=None, ge=1, le=65535)
    options: LlamaCppRuntimeOptions = Field(default_factory=LlamaCppRuntimeOptions)

    def effective_port(self) -> int:
        return self.port or self.options.port or _DEFAULT_PORTS[self.role]


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


def proven_gemma_mtp_options() -> LlamaCppRuntimeOptions:
    return LlamaCppRuntimeOptions(
        spec_type="draft-mtp", spec_draft_n_max=2, spec_draft_ngl=999,
        flash_attention="on", cache_type_k="q4_0", cache_type_v="q4_0",
        context_size=8192, parallel=1, gpu_layers=999, jinja=True,
    )


def recommended_embedding_options() -> LlamaCppRuntimeOptions:
    return LlamaCppRuntimeOptions(embeddings=True)


def recommended_reranker_options() -> LlamaCppRuntimeOptions:
    return LlamaCppRuntimeOptions(reranking=True)


def _fill_missing(current: dict[str, Any], defaults: LlamaCppRuntimeOptions) -> dict[str, Any]:
    for key, value in defaults.model_dump(mode="python", exclude_none=True).items():
        current.setdefault(key, value)
    return current


def _effective_profile(profile: LlamaProfile) -> LlamaProfile:
    current = profile.options.model_dump(mode="python", exclude_none=True)
    if profile.role == "embedding":
        current = _fill_missing(current, recommended_embedding_options())
    elif profile.role == "reranker":
        current = _fill_missing(current, recommended_reranker_options())
    elif profile.draft_model_path.strip() or current.get("spec_draft_model"):
        current = _fill_missing(current, proven_gemma_mtp_options())
        if profile.draft_model_path.strip():
            current["spec_draft_model"] = Path(profile.draft_model_path.strip().strip('"'))
    profile.options = LlamaCppRuntimeOptions.model_validate(current)
    return profile


@router.get("/profiles")
def list_profiles() -> dict[str, Any]:
    return {"profiles": _load(), "path": str(_profile_path())}


@router.get("/profiles/{role}")
def get_profile(role: Literal["llm", "embedding", "reranker"]) -> dict[str, Any]:
    raw = _load().get(role)
    profile = LlamaProfile.model_validate(raw) if raw else LlamaProfile(role=role)
    effective = _effective_profile(profile)
    return {"profile": effective.model_dump(mode="json"), "effective_port": effective.effective_port()}


@router.put("/profiles/{role}")
def put_profile(role: Literal["llm", "embedding", "reranker"], payload: LlamaProfile) -> dict[str, Any]:
    if payload.role != role:
        raise HTTPException(status_code=422, detail="profile role does not match URL")
    data = _load()
    if payload.port is not None:
        payload.options.port = payload.port
    effective = _effective_profile(payload)
    data[role] = effective.model_dump(mode="json")
    _save(data)
    return {"ok": True, "profile": data[role], "effective_port": effective.effective_port(), "path": str(_profile_path())}


@router.get("/presets/gemma-mtp")
def get_gemma_mtp_preset() -> dict[str, Any]:
    return {"preset": "gemma-mtp", "options": proven_gemma_mtp_options().model_dump(mode="json")}


@router.post("/presets/gemma-mtp/{role}")
def apply_gemma_mtp_preset(role: Literal["llm", "embedding", "reranker"]) -> dict[str, Any]:
    if role != "llm":
        raise HTTPException(status_code=422, detail="The Gemma MTP preset is an LLM preset.")
    data = _load()
    raw = data.get(role)
    profile = LlamaProfile.model_validate(raw) if raw else LlamaProfile(role=role)
    current = profile.options.model_dump(mode="python", exclude_none=True)
    current.update(proven_gemma_mtp_options().model_dump(mode="python", exclude_none=True))
    profile.options = LlamaCppRuntimeOptions.model_validate(current)
    if profile.draft_model_path.strip():
        profile.options.spec_draft_model = Path(profile.draft_model_path.strip().strip('"'))
    effective = _effective_profile(profile)
    data[role] = effective.model_dump(mode="json")
    _save(data)
    return {"ok": True, "preset": "gemma-mtp", "profile": data[role], "effective_port": effective.effective_port(), "path": str(_profile_path())}


@router.post("/command")
def render_command(payload: LlamaProfile) -> dict[str, Any]:
    if not payload.executable_path.strip():
        raise HTTPException(status_code=422, detail="executable_path is required")
    model_path = payload.model_path.strip() or None
    if payload.port is not None:
        payload.options.port = payload.port
    payload = _effective_profile(payload)
    command = payload.options.command(payload.executable_path.strip(), model_path=model_path)
    if payload.role == "llm" and get_settings().tools_enabled and "--jinja" not in command and "--no-jinja" not in command:
        command.append("--jinja")
    if payload.mmproj_path.strip() and "--mmproj" not in command:
        command.extend(["--mmproj", payload.mmproj_path.strip()])
    if payload.draft_model_path.strip() and "--model-draft" not in command:
        command.extend(["--model-draft", payload.draft_model_path.strip()])
    if "--port" not in command:
        command.extend(["--port", str(payload.effective_port())])
    return {"command": command, "shell_command": " ".join(_quote(item) for item in command), "role": payload.role, "effective_port": payload.effective_port()}


def _quote(value: str) -> str:
    if value and all(ch.isalnum() or ch in "._:/\\-=" for ch in value):
        return value
    return '"' + value.replace('"', '\\"') + '"'
