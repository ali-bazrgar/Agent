from pathlib import Path

from superagent.observability.diagnostics import DiagnosticStore


def test_diagnostic_span_records_success_and_duration(tmp_path: Path):
    store = DiagnosticStore(tmp_path)

    with store.span("llm.complete", execution_id="exec-1", request_id="req-1", provider="test"):
        pass

    events = [line for line in store.path.read_text(encoding="utf-8").splitlines() if line.strip()]
    assert len(events) == 2
    assert '"type":"operation.started"' in events[0]
    assert '"type":"operation.finished"' in events[1]
    assert '"operation":"llm.complete"' in events[1]
    assert '"status":"success"' in events[1]
    assert '"duration_ms":' in events[1]


def test_diagnostic_span_records_errors_without_swallowing(tmp_path: Path):
    store = DiagnosticStore(tmp_path)

    try:
        with store.span("reranker.rerank", execution_id="exec-2"):
            raise RuntimeError("provider unavailable")
    except RuntimeError:
        pass

    events = [line for line in store.path.read_text(encoding="utf-8").splitlines() if line.strip()]
    assert len(events) == 2
    assert '"status":"error"' in events[1]
    assert '"error_type":"RuntimeError"' in events[1]
    assert '"duration_ms":' in events[1]
