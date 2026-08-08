# Super Agent

Local-first AI orchestration platform with a Python application core and a React/Vite web UI.

## Architecture

- **API:** FastAPI under `src/superagent`
- **Web:** React + Vite + TypeScript
- **Runtime adapters:** llama.cpp-compatible HTTP providers
- **Storage:** SQLite with repository abstractions
- **RAG:** dense + lexical retrieval, reciprocal-rank fusion, reranking
- **Context:** deterministic context assembly with token budgeting and provenance
- **Agent:** routing, planning, criticism, verification, tools, and orchestration
- **Memory:** extraction, ranking, lifecycle, and consolidation
- **Learning:** flashcards, reviews, scheduling, and learning services

## Requirements

- Python 3.12+
- Node.js 20+
- npm 10+
- Optional local model servers compatible with the configured provider endpoints

## Development

### Python API

```bash
python -m venv .venv
# Windows: .venv\\Scripts\\activate
# Linux/macOS: source .venv/bin/activate
python -m pip install -e ".[dev]"
python -m pytest
uvicorn superagent.api.app:app --reload --host 127.0.0.1 --port 8000
```

API documentation is available at `/docs` while the server is running.

### Web UI

```bash
npm install
npm run typecheck
npm run dev
```

The development UI listens on port `3000` and proxies `/api/*` to `SUPERAGENT_API_URL` (default `http://127.0.0.1:8000`).

## Configuration

Copy `.env.example` to `.env` and adjust the `SUPERAGENT_*` variables for your environment. The API is deliberately provider-agnostic; model servers, database paths, timeouts, and execution limits are configuration rather than hard-coded application dependencies.

## Docker Compose

The production stack consists of separate API and web services:

```bash
docker compose up --build -d
```

Open `http://localhost:3000`. The web service proxies API requests to the internal FastAPI service. SQLite data and uploaded storage are persisted in the `superagent_data` volume.

For local model servers running on the host, the compose configuration defaults to `host.docker.internal` for the provider endpoints. Override these with `SUPERAGENT_LLM_BASE_URL`, `SUPERAGENT_EMBEDDING_BASE_URL`, and `SUPERAGENT_RERANKER_BASE_URL` when necessary.

## Testing

Run the Python test suite with:

```bash
python -m pytest -q
```

For coverage:

```bash
python -m pytest --cov=superagent --cov-report=term-missing
```

The frontend has a separate TypeScript gate:

```bash
npm run typecheck
```

## Project documentation

The `docs/` directory contains the architecture, ADRs, runtime specifications, security guidance, testing strategy, and implementation roadmap. Treat these documents as design references and keep them synchronized with production behavior.
