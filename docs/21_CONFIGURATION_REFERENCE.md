# Phase 9: Configuration Reference

## Environment Variables
The SuperAgent platform is configured via Pydantic BaseSettings using environment variables prefixed with `SUPERAGENT_`.

| Variable | Default | Description |
|---|---|---|
| `SUPERAGENT_ENVIRONMENT` | `development` | Runtime environment (`development`, `testing`, `production`) |
| `SUPERAGENT_DEBUG` | `false` | Enable debug logging and trace verbosity |
| `SUPERAGENT_APP_HOST` | `127.0.0.1` | Application bind host |
| `SUPERAGENT_APP_PORT` | `8000` | Application bind port |
| `SUPERAGENT_LOG_LEVEL` | `INFO` | Logging level (`DEBUG`, `INFO`, `WARNING`, `ERROR`) |
| `SUPERAGENT_DATABASE_PATH` | `data/superagent.sqlite3` | SQLite database file path |
| `SUPERAGENT_STORAGE_PATH` | `data/storage` | Local binary storage path |
| `SUPERAGENT_LLM_BASE_URL` | `http://127.0.0.1:8080` | Local llama.cpp / OpenAI-compatible LLM endpoint |
| `SUPERAGENT_EMBEDDING_BASE_URL` | `http://127.0.0.1:8081` | Embedding model endpoint |
| `SUPERAGENT_RERANKER_BASE_URL` | `http://127.0.0.1:8082` | Reranker model endpoint |
| `SUPERAGENT_PROVIDER_CONNECT_TIMEOUT_SECONDS` | `5.0` | Connection timeout for provider calls |
| `SUPERAGENT_PROVIDER_READ_TIMEOUT_SECONDS` | `30.0` | Read timeout for provider calls |
| `SUPERAGENT_MAX_TOOL_CALLS` | `8` | Maximum tool calls per execution |
| `SUPERAGENT_MAX_RETRIES` | `2` | Maximum retry attempts for transient failures |
