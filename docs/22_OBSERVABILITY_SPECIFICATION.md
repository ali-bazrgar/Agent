# Phase 9: Observability Specification

## Structured Logging & Tracing
- **Structured JSONL Diagnostics**: Each session records timestamp, event id, session id, request id, execution id, event type, duration and component fields under `data/diagnostics/`.
- **Secret Scrubbing**: Common API keys, Bearer tokens, passwords, secrets and access/refresh tokens are removed before persistence.
- **HTTP Tracing**: Every API request records method, path, query, status, duration and failures and returns an `x-request-id` response header.
- **Frontend Telemetry**: Diagnostic mode records UI clicks, visibility changes, unhandled errors/rejections, API status/duration and session metadata.
- **Execution Tracing**: Agent state transitions, model calls, tool calls, retries and execution diagnostics are recorded with execution/request correlation identifiers.

## Diagnostic workflow
1. Enable **Settings → Deep diagnostics**.
2. Reproduce the problem normally; no manual console copying is required.
3. Use **Export diagnostic session** to obtain a ZIP containing `events.jsonl` and a manifest.
4. Review/redact any application-specific content you do not want to share before sending the archive.

Diagnostics are intentionally file-backed and local-first. The export contains only the current diagnostic session; it is not uploaded by the application.
