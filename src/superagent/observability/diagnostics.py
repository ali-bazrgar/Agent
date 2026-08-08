from __future__ import annotations

import json
import re
import threading
import time
import uuid
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping

from superagent.config.settings import get_settings

_SECRET_KEYS = {"password", "secret", "authorization", "api_key", "apikey", "access_token", "refresh_token", "token", "client_secret"}
_SECRET_PATTERNS = (
    re.compile(r"(?i)(authorization\s*[:=]\s*bearer\s+)[^\s,}]+"),
    re.compile(r"(?i)(api[_-]?key\s*[:=]\s*)[^\s,}]+"),
    re.compile(r"(?i)(token\s*[:=]\s*)[^\s,}]+"),
)


def scrub(value: Any) -> Any:
    if isinstance(value, Mapping):
        return {
            str(k): scrub(v)
            for k, v in value.items()
            if str(k).strip().lower().replace("-", "_") not in _SECRET_KEYS
        }
    if isinstance(value, list):
        return [scrub(v) for v in value[:100]]
    if isinstance(value, tuple):
        return [scrub(v) for v in value[:100]]
    if isinstance(value, str):
        text = value[:10000]
        for pattern in _SECRET_PATTERNS:
            text = pattern.sub(r"\1[REDACTED]", text)
        return text
    return value


class DiagnosticStore:
    """Thread-safe JSONL diagnostic recorder with session export."""

    def __init__(self, root: Path | None = None) -> None:
        base = root or (get_settings().database_path_resolved.parent / "diagnostics")
        self.root = base
        self.root.mkdir(parents=True, exist_ok=True)
        self.session_id = uuid.uuid4().hex
        self._path = self.root / f"session-{self.session_id}.jsonl"
        self._lock = threading.Lock()

    def record(self, event_type: str, **fields: Any) -> dict[str, Any]:
        event = {"timestamp": datetime.now(timezone.utc).isoformat(), "monotonic_ms": round(time.monotonic() * 1000, 3), "session_id": self.session_id, "event_id": uuid.uuid4().hex, "type": event_type, **scrub(fields)}
        with self._lock:
            with self._path.open("a", encoding="utf-8") as handle:
                handle.write(json.dumps(event, ensure_ascii=False, separators=(",", ":")) + "\n")
        return event

    def export_zip(self) -> Path:
        stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        target = self.root / f"diagnostics-{self.session_id}-{stamp}.zip"
        with self._lock:
            with zipfile.ZipFile(target, "w", compression=zipfile.ZIP_DEFLATED) as archive:
                archive.write(self._path, arcname="events.jsonl")
                archive.writestr("manifest.json", json.dumps({"session_id": self.session_id, "created_at": stamp, "event_file": "events.jsonl", "note": "Credentials and common secrets are scrubbed before recording."}, indent=2))
        return target

    @property
    def path(self) -> Path:
        return self._path


_store: DiagnosticStore | None = None
_store_lock = threading.Lock()


def get_diagnostic_store() -> DiagnosticStore:
    global _store
    if _store is None:
        with _store_lock:
            if _store is None:
                _store = DiagnosticStore()
    return _store
