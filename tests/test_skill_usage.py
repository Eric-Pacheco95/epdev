"""Pytest tests for tools/scripts/skill_usage.py — aggregate_usage and to_heartbeat_metrics."""

import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from tools.scripts.skill_usage import aggregate_usage, to_heartbeat_metrics


def _now():
    return datetime.now(timezone.utc)


class TestAggregateUsage:
    def test_empty_invocations(self):
        result = aggregate_usage([])
        assert result["total_invocations_7d"] == 0
        assert result["total_invocations_30d"] == 0
        assert result["unique_skills_30d"] == 0

    def test_recent_invocations_counted(self):
        now = _now()
        invocations = [
            ("commit", now - timedelta(days=1)),
            ("commit", now - timedelta(days=2)),
            ("research", now - timedelta(days=3)),
        ]
        result = aggregate_usage(invocations)
        assert result["total_invocations_7d"] == 3
        assert result["total_invocations_30d"] == 3
        assert result["unique_skills_30d"] == 2

    def test_old_invocations_excluded(self):
        now = _now()
        invocations = [
            ("commit", now - timedelta(days=40)),
        ]
        result = aggregate_usage(invocations)
        assert result["total_invocations_30d"] == 0
        assert result["total_invocations_7d"] == 0

    def test_7d_vs_30d_split(self):
        now = _now()
        invocations = [
            ("commit", now - timedelta(days=2)),     # within 7d
            ("commit", now - timedelta(days=15)),    # within 30d only
        ]
        result = aggregate_usage(invocations)
        assert result["total_invocations_7d"] == 1
        assert result["total_invocations_30d"] == 2

    def test_tier_assignment_top(self):
        now = _now()
        invocations = [("commit", now - timedelta(hours=i)) for i in range(12)]
        result = aggregate_usage(invocations)
        assert result["tiers"]["commit"] == "top"

    def test_tier_assignment_mid(self):
        now = _now()
        invocations = [("review-code", now - timedelta(hours=i)) for i in range(5)]
        result = aggregate_usage(invocations)
        assert result["tiers"]["review-code"] == "mid"

    def test_tier_assignment_low(self):
        now = _now()
        invocations = [("visualize", now - timedelta(hours=1))]
        result = aggregate_usage(invocations)
        assert result["tiers"]["visualize"] == "low"

    def test_counts_30d_ordered(self):
        now = _now()
        invocations = [
            ("commit", now - timedelta(days=1)),
            ("commit", now - timedelta(days=2)),
            ("commit", now - timedelta(days=3)),
            ("research", now - timedelta(days=1)),
        ]
        result = aggregate_usage(invocations)
        keys = list(result["counts_30d"].keys())
        assert keys[0] == "commit"  # most frequent first


class TestToHeartbeatMetrics:
    def test_structure(self):
        usage = {
            "total_invocations_7d": 5,
            "total_invocations_30d": 20,
            "unique_skills_30d": 3,
            "counts_30d": {"commit": 10, "research": 7, "review-code": 3},
            "tiers": {"commit": "top", "research": "mid", "review-code": "low"},
        }
        metrics = to_heartbeat_metrics(usage)
        assert "skill_invocations_7d" in metrics
        assert "skill_invocations_30d" in metrics
        assert "unique_skills_30d" in metrics
        assert "skill_top5_30d" in metrics
        assert "skill_tiers" in metrics

    def test_values_correct(self):
        usage = {
            "total_invocations_7d": 5,
            "total_invocations_30d": 20,
            "unique_skills_30d": 3,
            "counts_30d": {"commit": 10},
            "tiers": {"commit": "top"},
        }
        metrics = to_heartbeat_metrics(usage)
        assert metrics["skill_invocations_7d"]["value"] == 5
        assert metrics["skill_invocations_30d"]["value"] == 20

    def test_empty_usage(self):
        usage = {
            "total_invocations_7d": 0,
            "total_invocations_30d": 0,
            "unique_skills_30d": 0,
            "counts_30d": {},
            "tiers": {},
        }
        metrics = to_heartbeat_metrics(usage)
        assert metrics["skill_top5_30d"]["value"] == "none"
