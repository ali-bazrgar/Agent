from __future__ import annotations

from pathlib import Path

from superagent.api.engine_manager import EngineManager
from superagent.api.llama_profiles import LlamaProfile


def test_engine_manager_builds_role_specific_commands(tmp_path: Path, monkeypatch) -> None:
    executable = tmp_path / "llama-server"
    model = tmp_path / "model.gguf"
    executable.write_text("stub", encoding="utf-8")
    model.write_text("stub", encoding="utf-8")

    profile = LlamaProfile(role="embedding", executable_path=str(executable), model_path=str(model))
    manager = EngineManager()
    monkeypatch.setattr(manager, "_profile", lambda role: profile)

    _, command = manager._command("embedding")

    assert command[0] == str(executable)
    assert "--model" in command
    assert str(model) in command
    assert "--embeddings" in command
    assert "--port" in command
    assert "8081" in command


def test_engine_manager_does_not_duplicate_explicit_port(tmp_path: Path, monkeypatch) -> None:
    executable = tmp_path / "llama-server"
    model = tmp_path / "model.gguf"
    executable.write_text("stub", encoding="utf-8")
    model.write_text("stub", encoding="utf-8")

    profile = LlamaProfile(role="reranker", executable_path=str(executable), model_path=str(model), options={"port": 19090})
    manager = EngineManager()
    monkeypatch.setattr(manager, "_profile", lambda role: profile)

    _, command = manager._command("reranker")

    assert command.count("--port") == 1
    assert "19090" in command
    assert "--reranking" in command


def test_gemma_mtp_failure_is_recognized() -> None:
    manager = EngineManager()
    assert manager._is_gemma_mtp_loader_failure(
        "failed to load draft model: invalid vector subscript"
    )
    assert manager._is_gemma_mtp_loader_failure(
        "Gemma4Assistant ... invalid vector subscript"
    )
    assert not manager._is_gemma_mtp_loader_failure("model loaded successfully")


def test_mtp_fallback_removes_speculative_flags() -> None:
    manager = EngineManager()
    command = [
        "llama-server.exe", "--model", "main.gguf",
        "--spec-type", "draft-mtp", "--model-draft", "draft.gguf",
        "--spec-draft-n-max", "2", "--gpu-layers-draft", "999",
        "--flash-attn", "on", "--port", "8080",
    ]
    fallback = manager._base_command_without_mtp(command)
    assert "--model" in fallback
    assert "main.gguf" in fallback
    assert "--port" in fallback
    assert "--model-draft" not in fallback
    assert "draft.gguf" not in fallback
    assert "--spec-type" not in fallback
    assert "--spec-draft-n-max" not in fallback
    assert "--gpu-layers-draft" not in fallback
