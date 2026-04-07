"""Tests for collectors/backlog_health.py collect_backlog_health."""

import json
import tempfile
from pathlib import Path

from tools.scripts.collectors.backlog_health import collect_backlog_health


def _write_backlog(path: Path, tasks: list[dict]) -> None:
    with path.open("w", encoding="utf-8") as f:
        for t in tasks:
            f.write(json.dumps(t) + "\n")


def _metric(results: list, name: str) -> dict:
    return next(r for r in results if r["name"] == name)


def test_collect_missing_backlog():
    results = collect_backlog_health(Path("/nonexistent/backlog.jsonl"))
    assert all(r["value"] is None for r in results)
    assert any("not found" in (r.get("detail") or "") for r in results)


def test_collect_empty_backlog():
    with tempfile.NamedTemporaryFile(suffix=".jsonl", delete=False) as f:
        path = Path(f.name)
    path.write_text("", encoding="utf-8")
    results = collect_backlog_health(path)
    total = _metric(results, "backlog_total_count")
    assert total["value"] == 0


def test_collect_counts_by_status():
    with tempfile.NamedTemporaryFile(suffix=".jsonl", delete=False) as f:
        path = Path(f.name)
    _write_backlog(path, [
        {"status": "pending"},
        {"status": "done"},
        {"status": "done"},
        {"status": "failed"},
    ])
    results = collect_backlog_health(path)
    assert _metric(results, "backlog_pending_count")["value"] == 1
    assert _metric(results, "backlog_done_count")["value"] == 2
    assert _metric(results, "backlog_failed_count")["value"] == 1
    assert _metric(results, "backlog_total_count")["value"] == 4


def test_collect_success_rate():
    with tempfile.NamedTemporaryFile(suffix=".jsonl", delete=False) as f:
        path = Path(f.name)
    _write_backlog(path, [
        {"status": "done"},
        {"status": "done"},
        {"status": "done"},
        {"status": "failed"},
    ])
    results = collect_backlog_health(path)
    rate = _metric(results, "backlog_success_rate")
    assert rate["value"] == 0.75


def test_collect_success_rate_none_when_no_terminal():
    with tempfile.NamedTemporaryFile(suffix=".jsonl", delete=False) as f:
        path = Path(f.name)
    _write_backlog(path, [{"status": "pending"}])
    results = collect_backlog_health(path)
    rate = _metric(results, "backlog_success_rate")
    assert rate["value"] is None


def test_collect_skips_malformed_lines():
    with tempfile.NamedTemporaryFile(suffix=".jsonl", delete=False) as f:
        path = Path(f.name)
    path.write_text('{"status": "done"}\nNOT JSON\n{"status": "pending"}\n', encoding="utf-8")
    results = collect_backlog_health(path)
    assert _metric(results, "backlog_total_count")["value"] == 2
