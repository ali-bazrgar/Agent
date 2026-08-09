from __future__ import annotations

from superagent.api.engine_manager import EngineManager


def test_engine_manager_recovers_persisted_process(monkeypatch, tmp_path) -> None:
    manager = EngineManager()
    monkeypatch.setattr(manager, "_state_path", lambda: tmp_path / "engine_processes.json")
    monkeypatch.setattr(manager, "_log_path", lambda role: tmp_path / f"{role}.log")
    monkeypatch.setattr(manager, "_pid_alive", staticmethod(lambda pid: pid == 12345))

    manager._save_state({
        "llm": {
            "pid": 12345,
            "started_at": 1000.0,
            "command": ["llama-server.exe", "--model", "model.gguf"],
            "log_path": str(tmp_path / "llm.log"),
        }
    })

    recovered = manager.status("llm")["llm"]
    assert recovered["running"] is True
    assert recovered["pid"] == 12345
    assert recovered["command"] == ["llama-server.exe", "--model", "model.gguf"]
