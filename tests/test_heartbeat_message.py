"""Tests for jarvis_heartbeat.build_message()."""

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

from tools.scripts.jarvis_heartbeat import build_message


def test_build_message_first_run():
    snap = {"ts": "2026-03-29T04:00:00Z", "metrics": {}}
    msg = build_message(snap, None, [])
    assert "2026-03-29T04:00:00Z" in msg
    assert "First heartbeat run" in msg
    assert "HEALTHY" in msg


def test_build_message_with_metrics():
    snap = {
        "ts": "2026-03-29T04:00:00Z",
        "metrics": {
            "signal_count": {"value": 156},
            "signal_velocity": {"value": 2.5},
            "failure_count": {"value": 3},
            "open_task_count": {"value": 51},
            "isc_ratio": {"value": 0.75},
            "sessions_per_day": {"value": 2.0},
        },
    }
    msg = build_message(snap, {"metrics": {}}, [])
    assert "Signals: 156" in msg
    assert "75.0%" in msg
    assert "HEALTHY" in msg


def test_build_message_with_warnings():
    snap = {"ts": "2026-03-29T04:00:00Z", "metrics": {}}
    changes = [{"severity": "WARN", "metric": "fail_rate", "previous": 0.05,
                "current": 0.15, "delta_pct": 200.0}]
    msg = build_message(snap, {"metrics": {}}, changes)
    assert "WARN" in msg
    assert "fail_rate" in msg
    assert "Threshold crossings" in msg


def test_build_message_critical_status():
    snap = {"ts": "2026-03-29T04:00:00Z", "metrics": {}}
    changes = [{"severity": "CRIT", "metric": "auth_health", "previous": 0,
                "current": 1, "delta_pct": 100.0}]
    msg = build_message(snap, {"metrics": {}}, changes)
    assert "Status: CRITICAL" in msg


def test_build_message_null_collectors():
    snap = {
        "ts": "2026-03-29T04:00:00Z",
        "metrics": {"broken_collector": {"value": None}},
    }
    msg = build_message(snap, None, [])
    assert "Collectors returning null" in msg
    assert "broken_collector" in msg
