from __future__ import annotations

import json
import os
import re
import signal
import subprocess
import threading
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Literal

from fastapi import APIRouter, HTTPException, Query

from superagent.api.llama_profiles import LlamaProfile, _DEFAULT_PORTS, _effective_profile, _load, _profile_path
from superagent.config.settings import get_settings

Role = Literal["llm", "embedding", "reranker"]
router = APIRouter(prefix="/engine", tags=["llama.cpp engine manager"])


@dataclass
class ManagedProcess:
    role: str
    process: subprocess.Popen[bytes] | None
    pid: int
    started_at: float
    command: list[str]
    log_path: str
    log_handle: Any = None


class EngineManager:
    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._processes: dict[str, ManagedProcess] = {}

    def _state_path(self) -> Path:
        settings = get_settings()
        settings.storage_path_resolved.mkdir(parents=True, exist_ok=True)
        return settings.storage_path_resolved / "engine_processes.json"

    def _load_state(self) -> dict[str, Any]:
        path = self._state_path()
        if not path.exists():
            return {}
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            return data if isinstance(data, dict) else {}
        except (OSError, json.JSONDecodeError):
            return {}

    def _save_state(self, data: dict[str, Any]) -> None:
        path = self._state_path()
        tmp = path.with_suffix(".tmp")
        tmp.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
        tmp.replace(path)

    def _persist(self, managed: ManagedProcess) -> None:
        data = self._load_state()
        data[managed.role] = {
            "pid": managed.pid,
            "started_at": managed.started_at,
            "command": managed.command,
            "log_path": managed.log_path,
        }
        self._save_state(data)

    def _forget(self, role: Role) -> None:
        data = self._load_state()
        if role in data:
            data.pop(role, None)
            self._save_state(data)

    @staticmethod
    def _pid_alive(pid: int) -> bool:
        if pid <= 0:
            return False
        try:
            os.kill(pid, 0)
        except ProcessLookupError:
            return False
        except PermissionError:
            return True
        except OSError:
            return False
        return True

    def _persisted(self, role: Role) -> ManagedProcess | None:
        raw = self._load_state().get(role)
        if not isinstance(raw, dict):
            return None
        try:
            pid = int(raw["pid"])
            started_at = float(raw.get("started_at", time.time()))
            command = [str(x) for x in raw.get("command", [])]
            log_path = str(raw.get("log_path", self._log_path(role)))
        except (KeyError, TypeError, ValueError):
            self._forget(role)
            return None
        if not self._pid_alive(pid):
            self._forget(role)
            return None
        return ManagedProcess(role, None, pid, started_at, command, log_path)

    def _profile(self, role: Role) -> LlamaProfile:
        raw = _load().get(role)
        profile = LlamaProfile.model_validate(raw) if raw else LlamaProfile(role=role)
        return _effective_profile(profile)

    def _executable(self, role: Role) -> str:
        profile = self._profile(role)
        executable = profile.executable_path.strip().strip('"')
        if not executable and role != "llm":
            executable = self._profile("llm").executable_path.strip().strip('"')
        if not executable:
            raise HTTPException(status_code=422, detail=f"{role}: llama-server executable path is required. Save the {role} profile or set the shared LLM executable path.")
        path = Path(executable).expanduser()
        if not path.is_file():
            raise HTTPException(status_code=422, detail=f"{role}: executable does not exist: {executable}")
        return str(path)

    def _command(self, role: Role) -> tuple[LlamaProfile, list[str]]:
        profile = self._profile(role)
        executable = self._executable(role)
        model = profile.model_path.strip().strip('"')
        if not model:
            raise HTTPException(status_code=422, detail=f"{role}: model path is required")
        model_path = Path(model).expanduser()
        if not model_path.is_file():
            raise HTTPException(status_code=422, detail=f"{role}: model does not exist: {model}")

        profile.options.port = profile.effective_port()
        command = profile.options.command(executable, model_path=str(model_path))
        if role == "llm" and get_settings().tools_enabled and "--jinja" not in command and "--no-jinja" not in command:
            command.append("--jinja")
        if role == "embedding" and profile.options.embeddings is not True:
            command.append("--embeddings")
        if role == "reranker" and profile.options.reranking is not True:
            command.append("--reranking")
        if not any(arg == "--port" for arg in command):
            command.extend(["--port", str(profile.effective_port())])
        if profile.mmproj_path.strip():
            mmproj = Path(profile.mmproj_path.strip().strip('"')).expanduser()
            if not mmproj.is_file():
                raise HTTPException(status_code=422, detail=f"{role}: MMProj does not exist: {mmproj}")
            command.extend(["--mmproj", str(mmproj)])
        if profile.draft_model_path.strip() and "--model-draft" not in command:
            draft = Path(profile.draft_model_path.strip().strip('"')).expanduser()
            if not draft.is_file():
                raise HTTPException(status_code=422, detail=f"{role}: draft/MTP model does not exist: {draft}")
            command.extend(["--model-draft", str(draft)])
        return profile, command

    def _log_path(self, role: str) -> Path:
        settings = get_settings()
        directory = settings.storage_path_resolved / "engines"
        directory.mkdir(parents=True, exist_ok=True)
        return directory / f"{role}.log"

    def _status_one(self, role: Role) -> dict[str, Any]:
        managed = self._processes.get(role)
        if managed and managed.process is not None and managed.process.poll() is not None:
            self._processes.pop(role, None)
            self._forget(role)
            managed = None
        if managed is None:
            managed = self._persisted(role)
        running = managed is not None and self._pid_alive(managed.pid)
        if not running:
            if managed is not None:
                self._forget(role)
            managed = None
        profile = self._profile(role)
        return {
            "running": running,
            "pid": managed.pid if managed else None,
            "started_at": datetime.fromtimestamp(managed.started_at, timezone.utc).isoformat() if managed else None,
            "command": managed.command if managed else None,
            "log_path": managed.log_path if managed else str(self._log_path(role)),
            "returncode": managed.process.poll() if managed and managed.process is not None else None,
            "default_port": _DEFAULT_PORTS[role],
            "port": profile.effective_port(),
        }

    def status(self, role: Role | None = None) -> dict[str, Any]:
        with self._lock:
            roles = [role] if role else list(_DEFAULT_PORTS)
            return {item: self._status_one(item) for item in roles}

    def start(self, role: Role) -> dict[str, Any]:
        with self._lock:
            existing = self._status_one(role)
            if existing["running"]:
                return existing
            _, command = self._command(role)
            log_path = self._log_path(role)
            log = open(log_path, "ab", buffering=0)
            creationflags = getattr(subprocess, "CREATE_NO_WINDOW", 0) if os.name == "nt" else 0
            try:
                process = subprocess.Popen(command, stdin=subprocess.DEVNULL, stdout=log, stderr=subprocess.STDOUT, creationflags=creationflags)
            except OSError as exc:
                log.close()
                raise HTTPException(status_code=502, detail=f"Unable to start {role}: {exc}") from exc
            managed = ManagedProcess(role, process, process.pid, time.time(), command, str(log_path), log)
            self._processes[role] = managed
            self._persist(managed)
            return self._status_one(role)

    def stop(self, role: Role) -> dict[str, Any]:
        with self._lock:
            managed = self._processes.get(role) or self._persisted(role)
            if not managed:
                return self._status_one(role)
            pid = managed.pid
            process = managed.process
            try:
                if process is not None:
                    if os.name == "nt":
                        process.terminate()
                    else:
                        os.kill(pid, signal.SIGTERM)
                    process.wait(timeout=8)
                elif os.name == "nt":
                    subprocess.run(["taskkill", "/PID", str(pid), "/T", "/F"], check=False, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                else:
                    os.kill(pid, signal.SIGTERM)
                    deadline = time.time() + 8
                    while self._pid_alive(pid) and time.time() < deadline:
                        time.sleep(0.1)
                    if self._pid_alive(pid):
                        os.kill(pid, signal.SIGKILL)
            except OSError as exc:
                if self._pid_alive(pid):
                    raise HTTPException(status_code=502, detail=f"Unable to stop {role} engine: {exc}") from exc
            finally:
                self._processes.pop(role, None)
                self._forget(role)
                if managed.log_handle:
                    try:
                        managed.log_handle.close()
                    except Exception:
                        pass
            return self._status_one(role)

    def restart(self, role: Role) -> dict[str, Any]:
        self.stop(role)
        return self.start(role)


manager = EngineManager()
_TPS_RE = re.compile(r"(?P<rate>\d+(?:\.\d+)?)\s+tokens\s+per\s+second", re.IGNORECASE)
_TOKEN_COUNT_RE = re.compile(r"(?:/|=)\s*(?P<count>\d+)\s+(?:tokens|runs)", re.IGNORECASE)
_PROMPT_MARKER = re.compile(r"prompt\s+eval", re.IGNORECASE)
_EVAL_MARKER = re.compile(r"(?:^|\s)eval\s+time", re.IGNORECASE)


def _empty_log(role: Role, path: Path) -> dict[str, Any]:
    return {"role": role, "path": str(path), "lines": [], "generation_tokens_per_second": None, "prompt_tokens_per_second": None, "generation_tokens": None, "prompt_tokens": None, "active_generation": False, "last_log_at": None, "note": "No llama.cpp generation has been observed yet."}


def _read_log(role: Role, lines: int) -> dict[str, Any]:
    path = manager._log_path(role)
    if not path.exists():
        return _empty_log(role, path)
    try:
        modified_at = path.stat().st_mtime
        with path.open("r", encoding="utf-8", errors="replace") as handle:
            tail = handle.readlines()[-lines:]
    except OSError as exc:
        raise HTTPException(status_code=500, detail=f"Unable to read {role} log: {exc}") from exc

    generation_rate = prompt_rate = None
    generation_tokens = prompt_tokens = None
    for line in reversed(tail):
        match = _TPS_RE.search(line)
        if not match:
            continue
        rate = float(match.group("rate"))
        count_match = _TOKEN_COUNT_RE.search(line)
        count = int(count_match.group("count")) if count_match else None
        if _PROMPT_MARKER.search(line) and prompt_rate is None:
            prompt_rate, prompt_tokens = rate, count
        elif _EVAL_MARKER.search(line) and generation_rate is None:
            generation_rate, generation_tokens = rate, count
        elif generation_rate is None:
            generation_rate, generation_tokens = rate, count

    running = bool(manager.status(role)[role]["running"])
    active_generation = running and (time.time() - modified_at) <= 5.0
    return {"role": role, "path": str(path), "lines": [line.rstrip("\r\n") for line in tail], "generation_tokens_per_second": generation_rate, "prompt_tokens_per_second": prompt_rate, "generation_tokens": generation_tokens, "prompt_tokens": prompt_tokens, "active_generation": active_generation, "last_log_at": datetime.fromtimestamp(modified_at, timezone.utc).isoformat(), "note": "Rates are historical llama.cpp measurements unless active_generation=true; the server does not generate tokens merely because it is running."}


@router.get("/status")
def engine_status() -> dict[str, Any]:
    return {"engines": manager.status(), "profile_path": str(_profile_path())}


@router.get("/status/{role}")
def engine_role_status(role: Role) -> dict[str, Any]:
    return manager.status(role)[role]


@router.get("/logs/{role}")
def engine_logs(role: Role, lines: int = Query(default=120, ge=10, le=1000)) -> dict[str, Any]:
    return _read_log(role, lines)


@router.post("/{role}/start")
def start_engine(role: Role) -> dict[str, Any]:
    return manager.start(role)


@router.post("/{role}/stop")
def stop_engine(role: Role) -> dict[str, Any]:
    return manager.stop(role)


@router.post("/{role}/restart")
def restart_engine(role: Role) -> dict[str, Any]:
    return manager.restart(role)
