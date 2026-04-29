"""Tests for collectors/backlog_health.py -- collect_backlog_health."""
from __future__ import annotations

import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))
if str(REPO_ROOT / "tools" / "scripts") not in sys.path:
    sys.path.insert(0, str(REPO_ROOT / "tools" / "scripts"))

from collectors.backlog_health import collect_backlog_health


def _metric(metrics, name):
    return next((m for m in metrics if m["name"] == name), None)


def _write_tasks(path, tasks):
    path.write_text("\n".join(json.dumps(t) for t in tasks) + "\n", encoding="utf-8")


class TestCollectBacklogHealth:
    def test_missing_file_returns_none_values(self, tmp_path):
        result = collect_backlog_health(tmp_path / "missing.jsonl")
        pending = _metric(result, "backlog_pending_count")
        assert pending is not None
        assert pending["value"] is None

    def test_empty_file_returns_zero_counts(self, tmp_path):
        f = tmp_path / "backlog.jsonl"
        f.write_text("", encoding="utf-8")
        result = collect_backlog_health(f)
        assert _metric(result, "backlog_pending_count")["value"] == 0
        assert _metric(result, "backlog_total_count")["value"] == 0

    def test_counts_pending_tasks(self, tmp_path):
        f = tmp_path / "backlog.jsonl"
        _write_tasks(f, [
            {"status": "pending"},
            {"status": "pending"},
            {"status": "done"},
        ])
        result = collect_backlog_health(f)
        assert _metric(result, "backlog_pending_count")["value"] == 2

    def test_counts_failed_and_done(self, tmp_path):
        f = tmp_path / "backlog.jsonl"
        _write_tasks(f, [
            {"status": "done"},
            {"status": "done"},
            {"status": "failed"},
        ])
        result = collect_backlog_health(f)
        assert _metric(result, "backlog_done_count")["value"] == 2
        assert _metric(result, "backlog_failed_count")["value"] == 1

    def test_success_rate_computed(self, tmp_path):
        f = tmp_path / "backlog.jsonl"
        _write_tasks(f, [
            {"status": "done"},
            {"status": "failed"},
        ])
        result = collect_backlog_health(f)
        rate = _metric(result, "backlog_success_rate")["value"]
        assert rate == 0.5

    def test_success_rate_none_when_no_terminal(self, tmp_path):
        f = tmp_path / "backlog.jsonl"
        _write_tasks(f, [{"status": "pending"}])
        result = collect_backlog_health(f)
        rate = _metric(result, "backlog_success_rate")
        assert rate["value"] is None

    def test_total_count_includes_all(self, tmp_path):
        f = tmp_path / "backlog.jsonl"
        _write_tasks(f, [
            {"status": "pending"},
            {"status": "done"},
            {"status": "failed"},
        ])
        result = collect_backlog_health(f)
        assert _metric(result, "backlog_total_count")["value"] == 3

    def test_malformed_json_lines_skipped(self, tmp_path):
        f = tmp_path / "backlog.jsonl"
        f.write_text(
            "not json\n" + json.dumps({"status": "pending"}) + "\n",
            encoding="utf-8",
        )
        result = collect_backlog_health(f)
        assert _metric(result, "backlog_pending_count")["value"] == 1
        assert _metric(result, "backlog_total_count")["value"] == 1

    def test_blank_lines_skipped(self, tmp_path):
        f = tmp_path / "backlog.jsonl"
        f.write_text(
            "\n" + json.dumps({"status": "done"}) + "\n\n",
            encoding="utf-8",
        )
        result = collect_backlog_health(f)
        assert _metric(result, "backlog_total_count")["value"] == 1

    def test_pending_review_counted_separately(self, tmp_path):
        f = tmp_path / "backlog.jsonl"
        _write_tasks(f, [{"status": "pending_review"}, {"status": "pending"}])
        result = collect_backlog_health(f)
        pr = _metric(result, "backlog_pending_review_count")
        assert pr is not None
        assert pr["value"] == 1

    def test_manual_review_counted(self, tmp_path):
        f = tmp_path / "backlog.jsonl"
        _write_tasks(f, [{"status": "manual_review"}])
        result = collect_backlog_health(f)
        mr = _metric(result, "backlog_manual_review_count")
        assert mr is not None
        assert mr["value"] == 1

    def test_all_done_success_rate_is_one(self, tmp_path):
        f = tmp_path / "backlog.jsonl"
        _write_tasks(f, [{"status": "done"}, {"status": "done"}])
        result = collect_backlog_health(f)
        assert _metric(result, "backlog_success_rate")["value"] == 1.0
