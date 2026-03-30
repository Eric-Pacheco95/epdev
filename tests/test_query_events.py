"""Pytest tests for tools/scripts/query_events.py — compute_metrics and status_badge."""

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from tools.scripts.query_events import compute_metrics, status_badge, THRESHOLDS


class TestComputeMetrics:
    def test_empty_records(self):
        m = compute_metrics([])
        assert m["sessions_total"] == 0
        assert m["total_tool_calls"] == 0
        assert m["failure_count"] == 0
        assert m["failure_rate"] == 0.0

    def test_counts_sessions_from_stop(self):
        records = [
            {"hook": "Stop", "session_id": "s1", "ts": "2026-03-01T10:00:00Z"},
            {"hook": "Stop", "session_id": "s2", "ts": "2026-03-01T14:00:00Z"},
        ]
        m = compute_metrics(records)
        assert m["sessions_total"] == 2

    def test_counts_tool_calls(self):
        records = [
            {"hook": "PostToolUse", "tool": "Read", "success": True, "session_id": "s1", "ts": "2026-03-01T10:00:00Z"},
            {"hook": "PostToolUse", "tool": "Edit", "success": True, "session_id": "s1", "ts": "2026-03-01T10:01:00Z"},
            {"hook": "PostToolUse", "tool": "Bash", "success": False, "session_id": "s1", "ts": "2026-03-01T10:02:00Z"},
        ]
        m = compute_metrics(records)
        assert m["total_tool_calls"] == 3
        assert m["failure_count"] == 1

    def test_failure_rate_calculation(self):
        records = [
            {"hook": "PostToolUse", "tool": "Read", "success": True, "session_id": "s1", "ts": "2026-03-01T10:00:00Z"},
            {"hook": "PostToolUse", "tool": "Bash", "success": False, "session_id": "s1", "ts": "2026-03-01T10:01:00Z"},
        ]
        m = compute_metrics(records)
        assert m["failure_rate"] == 0.5

    def test_excludes_session_tool(self):
        records = [
            {"hook": "PostToolUse", "tool": "_session", "success": True, "session_id": "s1", "ts": "2026-03-01T10:00:00Z"},
            {"hook": "PostToolUse", "tool": "Read", "success": True, "session_id": "s1", "ts": "2026-03-01T10:01:00Z"},
        ]
        m = compute_metrics(records)
        assert m["total_tool_calls"] == 1  # _session excluded

    def test_isc_gap_sessions(self):
        records = [
            {"hook": "PostToolUse", "tool": "Bash", "success": False, "session_id": "s1", "ts": "2026-03-01T10:00:00Z"},
            {"hook": "PostToolUse", "tool": "Read", "success": False, "session_id": "s2", "ts": "2026-03-01T11:00:00Z"},
            {"hook": "PostToolUse", "tool": "Edit", "success": True, "session_id": "s3", "ts": "2026-03-01T12:00:00Z"},
        ]
        m = compute_metrics(records)
        assert m["isc_gap_sessions"] == 2

    def test_top_tools(self):
        records = [
            {"hook": "PostToolUse", "tool": "Read", "success": True, "session_id": "s1", "ts": "2026-03-01T10:00:00Z"},
            {"hook": "PostToolUse", "tool": "Read", "success": True, "session_id": "s1", "ts": "2026-03-01T10:01:00Z"},
            {"hook": "PostToolUse", "tool": "Edit", "success": True, "session_id": "s1", "ts": "2026-03-01T10:02:00Z"},
        ]
        m = compute_metrics(records)
        assert m["top_tools"][0] == ("Read", 2)

    def test_cost_none_when_no_cost_data(self):
        records = [
            {"hook": "Stop", "session_id": "s1", "ts": "2026-03-01T10:00:00Z"},
        ]
        m = compute_metrics(records)
        assert m["cost_total_usd"] is None
        assert m["cost_avg_per_session_usd"] is None

    def test_cost_computed_when_present(self):
        records = [
            {"hook": "Stop", "session_id": "s1", "ts": "2026-03-01T10:00:00Z", "cost_usd": 0.05},
            {"hook": "Stop", "session_id": "s2", "ts": "2026-03-01T14:00:00Z", "cost_usd": 0.10},
        ]
        m = compute_metrics(records)
        assert m["cost_total_usd"] == 0.15
        assert m["cost_avg_per_session_usd"] == 0.075

    def test_intent_calls_counted(self):
        records = [
            {"hook": "PreToolUse", "tool": "Read", "ts": "2026-03-01T10:00:00Z"},
            {"hook": "PreToolUse", "tool": "Edit", "ts": "2026-03-01T10:01:00Z"},
        ]
        m = compute_metrics(records)
        assert m["intent_calls"] == 2


class TestStatusBadge:
    def test_failure_rate_ok(self):
        assert status_badge("failure_rate", 0.01) == "OK"

    def test_failure_rate_warn(self):
        assert status_badge("failure_rate", 0.06) == "WARN"

    def test_failure_rate_critical(self):
        assert status_badge("failure_rate", 0.20) == "CRITICAL"

    def test_sessions_per_day_ok(self):
        assert status_badge("sessions_per_day", 2.0) == "OK"

    def test_sessions_per_day_warn(self):
        assert status_badge("sessions_per_day", 0.3) == "WARN"

    def test_unknown_metric_ok(self):
        assert status_badge("unknown_metric", 999) == "OK"

    def test_failure_rate_at_boundary(self):
        assert status_badge("failure_rate", THRESHOLDS["failure_rate_warn"]) == "WARN"
        assert status_badge("failure_rate", THRESHOLDS["failure_rate_crit"]) == "CRITICAL"
