from __future__ import annotations

import os
import platform
from pathlib import Path
from typing import Literal

from fastapi import APIRouter, HTTPException
from fastapi.concurrency import run_in_threadpool
from pydantic import BaseModel

router = APIRouter(prefix="/system", tags=["system integration"])


class FilePickerRequest(BaseModel):
    kind: Literal["file", "directory"] = "file"
    title: str = "Select a file"
    extensions: list[str] = []
    initial_path: str | None = None


def _normalise_extensions(values: list[str]) -> list[str]:
    result: list[str] = []
    for value in values:
        value = value.strip().lower()
        if not value:
            continue
        if not value.startswith("."):
            value = "." + value
        result.append(value)
    return sorted(set(result))


def _pick(request: FilePickerRequest) -> str | None:
    try:
        import tkinter as tk
        from tkinter import filedialog
    except Exception as exc:  # pragma: no cover - platform dependent
        raise RuntimeError(f"Native file picker is unavailable: {exc}") from exc

    root = tk.Tk()
    root.withdraw()
    root.attributes("-topmost", True)
    try:
        initial = request.initial_path or str(Path.home())
        if request.kind == "directory":
            return filedialog.askdirectory(title=request.title, initialdir=initial) or None

        extensions = _normalise_extensions(request.extensions)
        filetypes = [("Supported files", " ".join(f"*{ext}" for ext in extensions))] if extensions else [("All files", "*")]
        return filedialog.askopenfilename(title=request.title, initialdir=initial, filetypes=filetypes) or None
    finally:
        root.destroy()


@router.post("/file-picker")
async def native_file_picker(request: FilePickerRequest) -> dict[str, str | None]:
    if platform.system() == "Linux" and not os.environ.get("DISPLAY") and not os.environ.get("WAYLAND_DISPLAY"):
        raise HTTPException(status_code=409, detail="No graphical desktop session is available for a native file picker.")
    try:
        selected = await run_in_threadpool(_pick, request)
    except Exception as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    return {"path": selected}
