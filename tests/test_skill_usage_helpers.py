"""Tests for skill_usage.py -- aggregate_usage, to_heartbeat_metrics."""
from __future__ import annotations

import importlib.util
from datetime import datetime, timezone, timedelta
from pathlib import Path

SCRIPT = Path(__file__).parents[1] / "tools" / "scripts" / "skill_usage.py"


def _load():
    spec = importlib.util.spec_from_file_location("skill_usage", SCRIPT)
    mod = importlib.util.module_from_spec(spec)  # type: ignore[arg-type]
    spec.loader.exec_module(mod)  # type: ignore[union-attr]
    return mod


def _ts(days_ago: float = 0) -> datetime:
    return datetime.now(timezone.utc) - timedelta(days=days_ago)


class TestAggregateUsage:
    def test_empty_invocations_returns_zeros(self):
        mod = _load()
        result = mod.aggregate_usage([])
        assert result["total_invocations_7d"] == 0
        assert result["total_invocations_30d"] == 0
        assert result["unique_skills_30d"] == 0

    def test_recent_invocations_counted_in_both_windows(self):
        mod = _load()
        invocations = [("commit", _ts(1)), ("commit", _ts(2))]
        result = mod.aggregate_usage(invocations)
        assert result["total_invocations_7d"] == 2
        assert result["total_invocations_30d"] == 2

    def test_old_invocations_outside_7d_excluded_from_7d(self):
        mod = _load()
        invocations = [("commit", _ts(10))]  # 10 days ago -- outside 7d
        result = mod.aggregate_usage(invocations)
        assert result["total_invocations_7d"] == 0
        assert result["total_invocations_30d"] == 1

    def test_old_invocations_outside_30d_excluded(self):
        mod = _load()
        invocations = [("commit", _ts(35))]  # 35 days ago -- outside both windows
        result = mod.aggregate_usage(invocations)
        assert result["total_invocations_30d"] == 0
        assert result["total_invocations_7d"] == 0

    def test_unique_skills_counted(self):
        mod = _load()
        invocations = [("commit", _ts(1)), ("research", _ts(2)), ("commit", _ts(3))]
        result = mod.aggregate_usage(invocations)
        assert result["unique_skills_30d"] == 2

    def test_tier_top_for_10_plus_uses(self):
        mod = _load()
        invocations = [("commit", _ts(i)) for i in range(10)]
        result = mod.aggregate_usage(invocations)
        assert result["tiers"]["commit"] == "top"

    def test_tier_mid_for_4_to_9_uses(self):
        mod = _load()
        invocations = [("research", _ts(i)) for i in range(5)]
        result = mod.aggregate_usage(invocations)
        assert result["tiers"]["research"] == "mid"

    def test_tier_low_for_under_4_uses(self):
        mod = _load()
        invocations = [("dream", _ts(1)), ("dream", _ts(2))]
        result = mod.aggregate_usage(invocations)
        assert result["tiers"]["dream"] == "low"


class TestToHeartbeatMetrics:
    def test_returns_all_required_metric_keys(self):
        mod = _load()
        usage = mod.aggregate_usage([("commit", _ts(1))])
        metrics = mod.to_heartbeat_metrics(usage)
        assert "skill_invocations_7d" in metrics
        assert "skill_invocations_30d" in metrics
        assert "unique_skills_30d" in metrics
        assert "skill_top5_30d" in metrics
        assert "skill_tiers" in metrics

    def test_each_metric_has_value_and_unit(self):
        mod = _load()
        usage = mod.aggregate_usage([])
        metrics = mod.to_heartbeat_metrics(usage)
        for key, entry in metrics.items():
            assert "value" in entry, f"{key} missing 'value'"
            assert "unit" in entry, f"{key} missing 'unit'"

    def test_top5_is_none_for_empty_usage(self):
        mod = _load()
        usage = mod.aggregate_usage([])
        metrics = mod.to_heartbeat_metrics(usage)
        assert metrics["skill_top5_30d"]["value"] == "none"

    def test_top5_shows_most_common_skills(self):
        mod = _load()
        invocations = [("commit", _ts(i)) for i in range(10)] + \
                      [("research", _ts(i)) for i in range(5)]
        usage = mod.aggregate_usage(invocations)
        metrics = mod.to_heartbeat_metrics(usage)
        top5 = metrics["skill_top5_30d"]["value"]
        assert "commit" in top5
