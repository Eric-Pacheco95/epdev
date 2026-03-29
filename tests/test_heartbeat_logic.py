"""Tests for jarvis_heartbeat -- severity evaluation and snapshot diffing."""

import sys
from pathlib import Path

# jarvis_heartbeat imports from tools.scripts.collectors.core via package path
REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

from tools.scripts.jarvis_heartbeat import _evaluate_severity, diff_snapshots


def test_evaluate_severity_no_thresholds():
    assert _evaluate_severity(42, {}) == "OK"


def test_evaluate_severity_crit_above():
    assert _evaluate_severity(100, {"crit_above": 90}) == "CRIT"
    assert _evaluate_severity(89, {"crit_above": 90}) == "OK"


def test_evaluate_severity_crit_below():
    assert _evaluate_severity(0.1, {"crit_below": 0.5}) == "CRIT"
    assert _evaluate_severity(0.6, {"crit_below": 0.5}) == "OK"


def test_evaluate_severity_warn_above():
    assert _evaluate_severity(80, {"warn_above": 70, "crit_above": 95}) == "WARN"


def test_evaluate_severity_warn_below():
    assert _evaluate_severity(0.3, {"warn_below": 0.5, "crit_below": 0.1}) == "WARN"


def test_evaluate_severity_crit_takes_priority():
    thresholds = {"warn_above": 50, "crit_above": 80}
    assert _evaluate_severity(85, thresholds) == "CRIT"
    assert _evaluate_severity(60, thresholds) == "WARN"
    assert _evaluate_severity(40, thresholds) == "OK"


def test_diff_snapshots_empty_previous():
    changes = diff_snapshots({"metrics": {"x": {"value": 5}}}, {}, {"collectors": []})
    assert changes == []


def test_diff_snapshots_basic():
    current = {"metrics": {"signal_count": {"value": 10}}}
    previous = {"metrics": {"signal_count": {"value": 8}}}
    cfg = {"collectors": [{"name": "signal_count", "thresholds": {}}]}
    changes = diff_snapshots(current, previous, cfg)
    assert len(changes) == 1
    assert changes[0]["delta"] == 2
    assert changes[0]["severity"] == "OK"


def test_diff_snapshots_with_threshold():
    current = {"metrics": {"fail_rate": {"value": 0.20}}}
    previous = {"metrics": {"fail_rate": {"value": 0.05}}}
    cfg = {"collectors": [
        {"name": "fail_rate", "thresholds": {"warn_above": 0.10, "crit_above": 0.25}}
    ]}
    changes = diff_snapshots(current, previous, cfg)
    assert changes[0]["severity"] == "WARN"


def test_diff_snapshots_skips_none_values():
    current = {"metrics": {"x": {"value": None}, "y": {"value": 5}}}
    previous = {"metrics": {"x": {"value": 3}, "y": {"value": 3}}}
    cfg = {"collectors": [{"name": "x"}, {"name": "y"}]}
    changes = diff_snapshots(current, previous, cfg)
    assert len(changes) == 1
    assert changes[0]["metric"] == "y"
