from superagent.api.llama_profiles import LlamaProfile


def test_profile_port_is_first_class_and_rendered():
    profile = LlamaProfile(role="llm", executable_path="llama-server.exe", model_path="model.gguf", port=9123)

    assert profile.effective_port() == 9123
    profile.options.port = profile.effective_port()
    command = profile.options.command(profile.executable_path, model_path=profile.model_path)

    assert "--port" in command
    assert command[command.index("--port") + 1] == "9123"


def test_role_defaults_are_distinct():
    assert LlamaProfile(role="llm").effective_port() == 8080
    assert LlamaProfile(role="embedding").effective_port() == 8081
    assert LlamaProfile(role="reranker").effective_port() == 8082
