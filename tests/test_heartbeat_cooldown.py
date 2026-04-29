"""Tests for jarvis_heartbeat cooldown and _evaluate_severity logic."""

import sys
from pathlib import Path
from datetime import datetime, timedelta, timezone

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

from tools.scripts.jarvis_heartbeat import _is_cooled_down, _evaluate_severity


def test_cooled_down_no_previous():
    assert _is_cooled_down("some_metric", {}, 60) is True


def test_cooled_down_enough_time_passed():
    old = (datetime.now(timezone.utc) - timedelta(minutes=120)).strftime("%Y-%m-%dT%H:%M:%SZ")
    state = {"my_metric": old}
    assert _is_cooled_down("my_metric", state, 60) is True


def test_not_cooled_down_recent():
    recent = (datetime.now(timezone.utc) - timedelta(minutes=5)).strftime("%Y-%m-%dT%H:%M:%SZ")
    state = {"my_metric": recent}
    assert _is_cooled_down("my_metric", state, 60) is False


def test_cooled_down_invalid_timestamp():
    state = {"my_metric": "not-a-timestamp"}
    assert _is_cooled_down("my_metric", state, 60) is True


def test_cooled_down_different_metric():
    recent = (datetime.now(timezone.utc) - timedelta(minutes=5)).strftime("%Y-%m-%dT%H:%M:%SZ")
    state = {"other_metric": recent}
    # my_metric has no entry -> cooled down
    assert _is_cooled_down("my_metric", state, 60) is True


class TestEvaluateSeverity:
    def test_no_thresholds_returns_ok(self):
        assert _evaluate_severity(100.0, {}) == "OK"

    def test_crit_above_triggers(self):
        assert _evaluate_severity(50.0, {"crit_above": 40.0}) == "CRIT"

    def test_crit_below_triggers(self):
        assert _evaluate_severity(5.0, {"crit_below": 10.0}) == "CRIT"

    def test_warn_above_triggers(self):
        assert _evaluate_severity(30.0, {"warn_above": 20.0, "crit_above": 50.0}) == "WARN"

    def test_warn_below_triggers(self):
        assert _evaluate_severity(2.0, {"warn_below": 5.0, "crit_below": 1.0}) == "WARN"

    def test_crit_takes_priority_over_warn(self):
        thresholds = {"warn_above": 10.0, "crit_above": 15.0}
        assert _evaluate_severity(20.0, thresholds) == "CRIT"

    def test_ok_when_within_bounds(self):
        thresholds = {"warn_above": 50.0, "crit_above": 80.0}
        assert _evaluate_severity(30.0, thresholds) == "OK"

    def test_exact_crit_boundary(self):
        assert _evaluate_severity(40.0, {"crit_above": 40.0}) == "CRIT"
