from __future__ import annotations

import shlex
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, Field


class LlamaCppRuntimeOptions(BaseModel):
    """Portable llama.cpp server options.

    Typed fields cover common and performance-critical options, including the
    speculative/MTP controls required by current llama.cpp builds. ``extra_args``
    remains available for forward compatibility with newer server flags.
    """

    threads: int | None = Field(default=None, ge=-1)
    threads_batch: int | None = Field(default=None, ge=-1)
    cpu_mask: str | None = None
    cpu_range: str | None = None
    cpu_strict: bool | None = None
    priority: int | None = Field(default=None, ge=-1, le=3)
    poll: int | None = Field(default=None, ge=0, le=100)
    context_size: int | None = Field(default=None, ge=0)
    predict: int | None = Field(default=None, ge=-1)
    batch_size: int | None = Field(default=None, ge=1)
    ubatch_size: int | None = Field(default=None, ge=1)
    keep: int | None = None
    flash_attention: Literal["on", "off", "auto"] | None = None
    rope_scaling: Literal["none", "linear", "yarn"] | None = None
    rope_scale: float | None = Field(default=None, gt=0)
    rope_freq_base: float | None = Field(default=None, gt=0)
    rope_freq_scale: float | None = Field(default=None, gt=0)
    yarn_orig_ctx: int | None = Field(default=None, ge=0)
    kv_offload: bool | None = None
    cache_type_k: str | None = None
    cache_type_v: str | None = None
    load_mode: Literal["none", "mmap", "mlock", "mmap+mlock", "dio"] | None = None
    numa: str | None = None
    devices: str | None = None
    gpu_layers: int | str | None = None
    split_mode: Literal["none", "layer", "row", "tensor"] | None = None
    tensor_split: str | None = None
    main_gpu: int | None = Field(default=None, ge=0)
    fit: Literal["on", "off"] | None = None
    fit_target: str | None = None
    fit_ctx: int | None = Field(default=None, ge=0)
    op_offload: bool | None = None
    cpu_moe: bool | None = None
    n_cpu_moe: int | None = Field(default=None, ge=0)
    lora: list[str] = Field(default_factory=list)
    lora_scaled: list[str] = Field(default_factory=list)
    control_vector: list[str] = Field(default_factory=list)
    control_vector_scaled: list[str] = Field(default_factory=list)

    samplers: str | None = None
    seed: int | None = None
    sampling_seq: str | None = None
    temperature: float | None = Field(default=None, ge=0)
    top_k: int | None = Field(default=None, ge=0)
    top_p: float | None = Field(default=None, gt=0, le=1)
    min_p: float | None = Field(default=None, ge=0, le=1)
    typical_p: float | None = Field(default=None, gt=0, le=1)
    repeat_last_n: int | None = Field(default=None, ge=0)
    repeat_penalty: float | None = Field(default=None, ge=0)
    presence_penalty: float | None = None
    frequency_penalty: float | None = None
    dry_multiplier: float | None = Field(default=None, ge=0)
    dry_base: float | None = Field(default=None, gt=0)
    dry_allowed_length: int | None = Field(default=None, ge=0)
    dry_penalty_last_n: int | None = Field(default=None, ge=0)
    mirostat: int | None = Field(default=None, ge=0, le=2)
    mirostat_lr: float | None = Field(default=None, ge=0)
    mirostat_ent: float | None = Field(default=None, ge=0)

    # Speculative decoding / MTP.
    spec_type: str | None = None
    spec_draft_model: Path | None = None
    spec_draft_threads: int | None = Field(default=None, ge=-1)
    spec_draft_threads_batch: int | None = Field(default=None, ge=-1)
    spec_draft_cpu_mask: str | None = None
    spec_draft_cpu_range: str | None = None
    spec_draft_cpu_strict: bool | None = None
    spec_draft_priority: int | None = Field(default=None, ge=-1, le=3)
    spec_draft_poll: int | None = Field(default=None, ge=0, le=100)
    spec_draft_device: str | None = None
    spec_draft_ngl: int | str | None = None
    spec_draft_n_max: int | None = Field(default=None, ge=0)
    spec_draft_n_min: int | None = Field(default=None, ge=0)
    spec_draft_cpu_moe: bool | None = None
    spec_draft_n_cpu_moe: int | None = Field(default=None, ge=0)
    spec_draft_cache_type_k: str | None = None
    spec_draft_cache_type_v: str | None = None
    spec_draft_backend_sampling: bool | None = None
    draft_p_split: float | None = Field(default=None, ge=0, le=1)
    draft_p_min: float | None = Field(default=None, ge=0, le=1)

    pooling: Literal["none", "mean", "cls", "last", "rank"] | None = None
    parallel: int | None = Field(default=None, ge=-1)
    continuous_batching: bool | None = None
    cache_prompt: bool | None = None
    cache_reuse: int | None = Field(default=None, ge=0)
    context_shift: bool | None = None
    warmup: bool | None = None
    reasoning: Literal["on", "off", "auto"] | None = None
    reasoning_budget: int | None = Field(default=None, ge=-1)
    reasoning_preserve: bool | None = None
    reasoning_format: Literal["none", "deepseek", "deepseek-legacy"] | None = None
    jinja: bool | None = None
    chat_template: str | None = None
    alias: str | None = None
    host: str | None = None
    port: int | None = Field(default=None, ge=1, le=65535)
    api_key: str | None = None
    metrics: bool | None = None
    props: bool | None = None
    slots: bool | None = None
    models_dir: Path | None = None
    models_max: int | None = Field(default=None, ge=0)
    models_autoload: bool | None = None
    embeddings: bool | None = None
    reranking: bool | None = None
    ui: bool | None = None
    timeout: int | None = Field(default=None, ge=1)

    extra_args: dict[str, Any] = Field(default_factory=dict)

    def to_cli_args(self) -> list[str]:
        """Render configured values into deterministic llama.cpp CLI arguments."""
        mapping = {
            "threads": "--threads", "threads_batch": "--threads-batch", "cpu_mask": "--cpu-mask",
            "cpu_range": "--cpu-range", "cpu_strict": "--cpu-strict", "priority": "--prio",
            "poll": "--poll", "context_size": "--ctx-size", "predict": "--predict",
            "batch_size": "--batch-size", "ubatch_size": "--ubatch-size", "keep": "--keep",
            "flash_attention": "--flash-attn", "rope_scaling": "--rope-scaling", "rope_scale": "--rope-scale",
            "rope_freq_base": "--rope-freq-base", "rope_freq_scale": "--rope-freq-scale",
            "yarn_orig_ctx": "--yarn-orig-ctx", "kv_offload": "--kv-offload",
            "cache_type_k": "--cache-type-k", "cache_type_v": "--cache-type-v", "load_mode": "--load-mode",
            "numa": "--numa", "devices": "--device", "gpu_layers": "--gpu-layers", "split_mode": "--split-mode",
            "tensor_split": "--tensor-split", "main_gpu": "--main-gpu", "fit": "--fit", "fit_target": "--fit-target",
            "fit_ctx": "--fit-ctx", "op_offload": "--op-offload", "cpu_moe": "--cpu-moe", "n_cpu_moe": "--n-cpu-moe",
            "samplers": "--samplers", "seed": "--seed", "sampling_seq": "--sampler-seq", "temperature": "--temperature",
            "top_k": "--top-k", "top_p": "--top-p", "min_p": "--min-p", "typical_p": "--typical-p",
            "repeat_last_n": "--repeat-last-n", "repeat_penalty": "--repeat-penalty", "presence_penalty": "--presence-penalty",
            "frequency_penalty": "--frequency-penalty", "dry_multiplier": "--dry-multiplier", "dry_base": "--dry-base",
            "dry_allowed_length": "--dry-allowed-length", "dry_penalty_last_n": "--dry-penalty-last-n",
            "mirostat": "--mirostat", "mirostat_lr": "--mirostat-lr", "mirostat_ent": "--mirostat-ent",
            "spec_type": "--spec-type", "spec_draft_model": "--model-draft", "spec_draft_threads": "--threads-draft",
            "spec_draft_threads_batch": "--threads-batch-draft", "spec_draft_cpu_mask": "--cpu-mask-draft",
            "spec_draft_cpu_range": "--cpu-range-draft", "spec_draft_cpu_strict": "--cpu-strict-draft",
            "spec_draft_priority": "--prio-draft", "spec_draft_poll": "--poll-draft", "spec_draft_device": "--device-draft",
            "spec_draft_ngl": "--gpu-layers-draft", "spec_draft_n_max": "--spec-draft-n-max", "spec_draft_n_min": "--spec-draft-n-min",
            "spec_draft_cpu_moe": "--cpu-moe-draft", "spec_draft_n_cpu_moe": "--n-cpu-moe-draft",
            "spec_draft_cache_type_k": "--cache-type-k-draft", "spec_draft_cache_type_v": "--cache-type-v-draft",
            "spec_draft_backend_sampling": "--spec-draft-backend-sampling", "draft_p_split": "--draft-p-split", "draft_p_min": "--draft-p-min",
            "pooling": "--pooling", "parallel": "--parallel", "continuous_batching": "--cont-batching", "cache_prompt": "--cache-prompt",
            "cache_reuse": "--cache-reuse", "context_shift": "--context-shift", "warmup": "--warmup",
            "reasoning": "--reasoning", "reasoning_budget": "--reasoning-budget", "reasoning_preserve": "--reasoning-preserve",
            "reasoning_format": "--reasoning-format", "jinja": "--jinja", "chat_template": "--chat-template", "alias": "--alias",
            "host": "--host", "port": "--port", "api_key": "--api-key", "metrics": "--metrics", "props": "--props",
            "slots": "--slots", "models_dir": "--models-dir", "models_max": "--models-max", "models_autoload": "--models-autoload",
            "embeddings": "--embeddings", "reranking": "--reranking", "ui": "--ui", "timeout": "--timeout",
        }
        args: list[str] = []
        data = self.model_dump(exclude={"extra_args"}, exclude_none=True)
        for key, flag in mapping.items():
            if key not in data:
                continue
            value = data[key]
            if isinstance(value, bool):
                args.append(flag if value else f"--no-{flag.removeprefix('--')}")
            elif isinstance(value, list):
                for item in value:
                    args.extend([flag, str(item)])
            else:
                args.extend([flag, str(value)])
        for key, value in sorted(self.extra_args.items()):
            flag = key if key.startswith("--") else f"--{key}"
            if isinstance(value, bool):
                args.append(flag if value else f"--no-{flag.removeprefix('--')}")
            elif isinstance(value, list):
                for item in value:
                    args.extend([flag, str(item)])
            else:
                args.extend([flag, str(value)])
        return args

    def command(self, server_path: str | Path, *, model_path: str | Path | None = None) -> list[str]:
        command = [str(server_path)]
        if model_path is not None:
            command.extend(["--model", str(model_path)])
        return command + self.to_cli_args()

    def shell_command(self, server_path: str | Path, *, model_path: str | Path | None = None) -> str:
        return shlex.join(self.command(server_path, model_path=model_path))
