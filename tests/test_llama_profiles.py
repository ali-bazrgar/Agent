from pathlib import Path

from superagent.api.llama_profiles import (
    LlamaProfile,
    _effective_profile,
    recommended_embedding_options,
    recommended_reranker_options,
)


def test_embedding_profile_gets_dedicated_server_mode() -> None:
    profile = _effective_profile(LlamaProfile(role="embedding"))
    assert profile.options.embeddings is True
    assert profile.options.reranking is None


def test_reranker_profile_gets_dedicated_server_mode() -> None:
    profile = _effective_profile(LlamaProfile(role="reranker"))
    assert profile.options.reranking is True
    assert profile.options.embeddings is None


def test_mtp_defaults_do_not_overwrite_explicit_performance_settings() -> None:
    profile = LlamaProfile(
        role="llm",
        draft_model_path="D:/models/draft.gguf",
        options={"context_size": 4096, "gpu_layers": 12, "temperature": 0.2},
    )
    effective = _effective_profile(profile)
    assert effective.options.context_size == 4096
    assert effective.options.gpu_layers == 12
    assert effective.options.temperature == 0.2
    assert effective.options.spec_type == "draft-mtp"
    assert effective.options.spec_draft_n_max == 2
    assert effective.options.spec_draft_ngl == 999
    assert effective.options.spec_draft_model == Path("D:/models/draft.gguf")


def test_role_presets_are_explicit_and_independent() -> None:
    assert recommended_embedding_options().embeddings is True
    assert recommended_reranker_options().reranking is True
