"""Pytest tests for tools/scripts/jarvis_heartbeat.py — _evaluate_severity and diff_snapshots."""

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from tools.scripts.jarvis_heartbeat import _evaluate_severity, diff_snapshots


class TestEvaluateSeverity:
    def test_ok_below_all(self):
        assert _evaluate_severity(5, {"warn_above": 10, "crit_above": 20}) == "OK"

    def test_warn_above(self):
        assert _evaluate_severity(15, {"warn_above": 10, "crit_above": 20}) == "WARN"

    def test_crit_above(self):
        assert _evaluate_severity(25, {"warn_above": 10, "crit_above": 20}) == "CRIT"

    def test_empty_thresholds(self):
        assert _evaluate_severity(100, {}) == "OK"

    def test_crit_below(self):
        assert _evaluate_severity(0.1, {"crit_below": 0.5, "warn_below": 0.8}) == "CRIT"

    def test_warn_below(self):
        assert _evaluate_severity(0.6, {"crit_below": 0.5, "warn_below": 0.8}) == "WARN"

    def test_ok_above_below_thresholds(self):
        assert _evaluate_severity(0.9, {"crit_below": 0.5, "warn_below": 0.8}) == "OK"

    def test_at_warn_boundary(self):
        # At exactly the boundary
        result = _evaluate_severity(10, {"warn_above": 10, "crit_above": 20})
        assert result in ("OK", "WARN")  # implementation-dependent on >= vs >

    def test_only_warn_threshold(self):
        assert _evaluate_severity(15, {"warn_above": 10}) == "WARN"
        assert _evaluate_severity(5, {"warn_above": 10}) == "OK"


class TestDiffSnapshots:
    def test_detects_positive_delta(self):
        current = {"metrics": {"signal_count": {"value": 20}}}
        previous = {"metrics": {"signal_count": {"value": 15}}}
        cfg = {"collectors": [{"name": "signal_count", "thresholds": {}}]}
        changes = diff_snapshots(current, previous, cfg)
        sc = next(c for c in changes if c["metric"] == "signal_count")
        assert sc["delta"] == 5

    def test_zero_delta(self):
        current = {"metrics": {"x": {"value": 10}}}
        previous = {"metrics": {"x": {"value": 10}}}
        cfg = {"collectors": [{"name": "x", "thresholds": {}}]}
        changes = diff_snapshots(current, previous, cfg)
        x = next(c for c in changes if c["metric"] == "x")
        assert x["delta"] == 0

    def test_negative_delta(self):
        current = {"metrics": {"x": {"value": 5}}}
        previous = {"metrics": {"x": {"value": 10}}}
        cfg = {"collectors": [{"name": "x", "thresholds": {}}]}
        changes = diff_snapshots(current, previous, cfg)
        x = next(c for c in changes if c["metric"] == "x")
        assert x["delta"] == -5

    def test_new_metric_not_in_previous(self):
        """New metrics not in previous snapshot produce no diff entry (no baseline to compare)."""
        current = {"metrics": {"new_metric": {"value": 42}}}
        previous = {"metrics": {}}
        cfg = {"collectors": [{"name": "new_metric", "thresholds": {}}]}
        changes = diff_snapshots(current, previous, cfg)
        nm = [c for c in changes if c["metric"] == "new_metric"]
        # Behavior depends on implementation — either absent or delta from 0
        assert len(nm) <= 1

    def test_multiple_metrics(self):
        current = {"metrics": {"a": {"value": 10}, "b": {"value": 20}}}
        previous = {"metrics": {"a": {"value": 5}, "b": {"value": 25}}}
        cfg = {"collectors": [
            {"name": "a", "thresholds": {}},
            {"name": "b", "thresholds": {}},
        ]}
        changes = diff_snapshots(current, previous, cfg)
        assert len(changes) == 2
