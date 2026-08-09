from __future__ import annotations

import os
import signal
import subprocess
import threading
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Literal

from fastapi import APIRouter, HTTPException

from superagent.api.llama_profiles import LlamaProfile, _load, _profile_path
from superagent.config.settings import get_settings

Role = Literal["llm", "embedding", "reranker"]
router = APIRouter(prefix="/engine", tags=["llama.cpp engine manager"])

_DEFAULT_PORTS: dict[str, int] = {"llm": 8080, "embedding": 8081, "reranker": 8082}


@dataclass
class ManagedProcess:
    role: str
    process: subprocess.Popen[bytes]
    started_at: float
    command: list[str]
    log_path: str


class EngineManager:
    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._processes: dict[str, ManagedProcess] = {}

    def _profile(self, role: Role) -> LlamaProfile:
        raw = _load().get(role)
        return LlamaProfile.model_validate(raw) if raw else LlamaProfile(role=role)

    def _command(self, role: Role) -> tuple[LlamaProfile, list[str]]:
        profile = self._profile(role)
        executable = profile.executable_path.strip()
        if not executable:
            raise HTTPException(status_code=422, detail=f"{role}: llama-server executable path is required")
        if not Path(executable).exists():
            raise HTTPException(status_code=422, detail=f"{role}: executable does not exist: {executable}")
        model = profile.model_path.strip()
        if role != "llm" and not model:
            raise HTTPException(status_code=422, detail=f"{role}: model path is required")
        if model and not Path(model).exists():
            raise HTTPException(status_code=422, detail=f"{role}: model does not exist: {model}")

        command = profile.options.command(executable, model_path=model or None)
        if role == "embedding" and profile.options.embeddings is not True:
            command.append("--embeddings")
        if role == "reranker" and profile.options.reranking is not True:
            command.append("--reranking")
        if not any(arg == "--port" for arg in command):
            command.extend(["--port", str(_DEFAULT_PORTS[role])])
        if profile.mmproj_path.strip():
            command.extend(["--mmproj", profile.mmproj_path.strip()])
        if profile.draft_model_path.strip() and "--model-draft" not in command:
            command.extend(["--model-draft", profile.draft_model_path.strip()])
        return profile, command

    def _log_path(self, role: str) -> Path:
        settings = get_settings()
        directory = settings.storage_path_resolved / "engines"
        directory.mkdir(parents=True, exist_ok=True)
        return directory / f"{role}.log"

    def status(self, role: Role | None = None) -> dict[str, Any]:
        with self._lock:
            roles = [role] if role else list(_DEFAULT_PORTS)
            result: dict[str, Any] = {}
            for item in roles:
                managed = self._processes.get(item)
                running = bool(managed and managed.process.poll() is None)
                result[item] = {
                    "running": running,
                    "pid": managed.process.pid if managed else None,
                    "started_at": datetime.fromtimestamp(managed.started_at, timezone.utc).isoformat() if managed else None,
                    "command": managed.command if managed else None,
                    "log_path": managed.log_path if managed else str(self._log_path(item)),
                    "returncode": managed.process.poll() if managed else None,
                    "default_port": _DEFAULT_PORTS[item],
                }
            return result

    def start(self, role: Role) -> dict[str, Any]:
        with self._lock:
            existing = self._processes.get(role)
            if existing and existing.process.poll() is None:
                return self.status(role)[role]
            profile, command = self._command(role)
            log_path = self._log_path(role)
            log = open(log_path, "ab", buffering=0)
            creationflags = getattr(subprocess, "CREATE_NO_WINDOW", 0) if os.name == "nt" else 0
            try:
                process = subprocess.Popen(command, stdin=subprocess.DEVNULL, stdout=log, stderr=subprocess.STDOUT, creationflags=creationflags)
            except OSError as exc:
                log.close()
                raise HTTPException(status_code=502, detail=f"Unable to start {role}: {exc}") from exc
            managed = ManagedProcess(role, process, time.time(), command, str(log_path))
            self._processes[role] = managed
            return self.status(role)[role]

    def stop(self, role: Role) -> dict[str, Any]:
        with self._lock:
            managed = self._processes.get(role)
            if not managed or managed.process.poll() is not None:
                return self.status(role)[role]
            process = managed.process
            try:
                if os.name == "nt":
                    process.terminate()
                else:
                    os.kill(process.pid, signal.SIGTERM)
                process.wait(timeout=8)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait(timeout=3)
            return self.status(role)[role]

    def restart(self, role: Role) -> dict[str, Any]:
        self.stop(role)
        return self.start(role)


manager = EngineManager()


@router.get("/status")
def engine_status() -> dict[str, Any]:
    return {"engines": manager.status(), "profile_path": str(_profile_path())}


@router.get("/status/{role}")
def engine_role_status(role: Role) -> dict[str, Any]:
    return manager.status(role)[role]


@router.post("/{role}/start")
def start_engine(role: Role) -> dict[str, Any]:
    return manager.start(role)


@router.post("/{role}/stop")
def stop_engine(role: Role) -> dict[str, Any]:
    return manager.stop(role)


@router.post("/{role}/restart")
def restart_engine(role: Role) -> dict[str, Any]:
    return manager.restart(role)
