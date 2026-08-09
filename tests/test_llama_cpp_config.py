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


def test_gemma_mtp_profile_reproduces_proven_runtime_flags():
    options = LlamaCppRuntimeOptions(
        spec_type="draft-mtp",
        spec_draft_model="mtp-gemma-4-E2B-it.gguf",
        spec_draft_n_max=2,
        spec_draft_ngl=999,
        flash_attention="on",
        cache_type_k="q4_0",
        cache_type_v="q4_0",
        context_size=8192,
        parallel=1,
        gpu_layers=999,
    )
    command = options.command("llama-server.exe", model_path="gemma-4-E2B-it-qat-UD-Q4_K_XL.gguf")
    assert command == [
        "llama-server.exe",
        "--model", "gemma-4-E2B-it-qat-UD-Q4_K_XL.gguf",
        "--ctx-size", "8192",
        "--flash-attn", "on",
        "--cache-type-k", "q4_0",
        "--cache-type-v", "q4_0",
        "--gpu-layers", "999",
        "--spec-type", "draft-mtp",
        "--model-draft", "mtp-gemma-4-E2B-it.gguf",
        "--gpu-layers-draft", "999",
        "--spec-draft-n-max", "2",
        "--parallel", "1",
    ]


def test_llama_cpp_options_render_draft_device_and_kv_controls():
    options = LlamaCppRuntimeOptions(
        spec_type="draft-mtp",
        spec_draft_device="CUDA0",
        spec_draft_cache_type_k="q4_0",
        spec_draft_cache_type_v="q4_0",
        spec_draft_threads_batch=4,
        spec_draft_backend_sampling=False,
    )
    command = options.command("llama-server.exe", model_path="model.gguf")
    assert "--device-draft" in command and "CUDA0" in command
    assert "--cache-type-k-draft" in command and "q4_0" in command
    assert "--cache-type-v-draft" in command and "q4_0" in command
    assert "--threads-batch-draft" in command and "4" in command
    assert "--no-spec-draft-backend-sampling" in command
