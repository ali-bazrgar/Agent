from superagent.llm.llama_cpp_config import LlamaCppRuntimeOptions


def test_llama_cpp_options_render_core_runtime_flags():
    options = LlamaCppRuntimeOptions(
        threads=8,
        context_size=32768,
        flash_attention="on",
        gpu_layers="all",
        spec_type="draft-mtp",
        extra_args={"cache-type-k": "q8_0"},
    )
    command = options.command("llama-server.exe", model_path="model.gguf")
    assert command[:3] == ["llama-server.exe", "--model", "model.gguf"]
    assert "--threads" in command and "8" in command
    assert "--ctx-size" in command and "32768" in command
    assert "--flash-attn" in command and "on" in command
    assert "--gpu-layers" in command and "all" in command
    assert "--spec-type" in command and "draft-mtp" in command
    assert "--cache-type-k" in command and "q8_0" in command


def test_llama_cpp_options_render_reasoning_controls():
    options = LlamaCppRuntimeOptions(reasoning="auto", reasoning_budget=2048, reasoning_preserve=False)
    command = options.command("llama-server.exe", model_path="model.gguf")
    assert "--reasoning" in command and "auto" in command
    assert "--reasoning-budget" in command and "2048" in command
    assert "--no-reasoning-preserve" in command
