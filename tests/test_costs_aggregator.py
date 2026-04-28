"""Tests for costs_aggregator.py -- pure helper functions."""
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

import pytest
from datetime import datetime, timedelta, timezone
from tools.scripts.costs_aggregator import compute_cost, extract_text, _empty_window, load_pricing, build_window


class TestComputeCost:
    def test_zero_usage_returns_zero(self):
        assert compute_cost({}, {}) == 0.0

    def test_input_tokens_only(self):
        rates = {"input_per_mtok": 3.0, "output_per_mtok": 0, "cache_read_per_mtok": 0, "cache_creation_per_mtok": 0}
        result = compute_cost({"input_tokens": 1_000_000}, rates)
        assert result == pytest.approx(3.0)

    def test_output_tokens_only(self):
        rates = {"input_per_mtok": 0, "output_per_mtok": 15.0, "cache_read_per_mtok": 0, "cache_creation_per_mtok": 0}
        result = compute_cost({"output_tokens": 1_000_000}, rates)
        assert result == pytest.approx(15.0)

    def test_combined_usage(self):
        rates = {"input_per_mtok": 3.0, "output_per_mtok": 15.0, "cache_read_per_mtok": 0.3, "cache_creation_per_mtok": 3.75}
        usage = {"input_tokens": 500_000, "output_tokens": 100_000, "cache_read_input_tokens": 0, "cache_creation_input_tokens": 0}
        result = compute_cost(usage, rates)
        assert result == pytest.approx(1.5 + 1.5)

    def test_missing_rate_keys_treated_as_zero(self):
        result = compute_cost({"input_tokens": 1_000_000}, {})
        assert result == 0.0


class TestExtractText:
    def test_string_input_returned_as_is(self):
        assert extract_text("hello") == "hello"

    def test_empty_string(self):
        assert extract_text("") == ""

    def test_list_with_text_blocks(self):
        content = [{"type": "text", "text": "hello"}, {"type": "text", "text": "world"}]
        assert extract_text(content) == "hello world"

    def test_list_skips_non_text_blocks(self):
        content = [{"type": "tool_use", "id": "x"}, {"type": "text", "text": "hi"}]
        assert extract_text(content) == "hi"

    def test_non_string_non_list_returns_empty(self):
        assert extract_text(None) == ""
        assert extract_text(42) == ""

    def test_empty_list(self):
        assert extract_text([]) == ""


class TestEmptyWindow:
    def test_structure(self):
        w = _empty_window(25.0)
        assert w["spend_usd"] == 0.0
        assert w["budget"]["monthly_usd"] == 25.0
        assert w["budget"]["pct"] == 0
        assert w["daily_spend_usd"] == []

    def test_budget_propagates(self):
        w = _empty_window(50.0)
        assert w["budget"]["monthly_usd"] == 50.0


class TestLoadPricing:
    def test_reads_models_and_budget(self, tmp_path):
        import json as _json
        p = tmp_path / "pricing.json"
        data = {"claude": {"models": {"sonnet": {"input_per_mtok": 3.0}}, "monthly_budget_usd": 30.0}}
        p.write_text(_json.dumps(data))
        models, budget = load_pricing(p)
        assert "sonnet" in models
        assert budget == 30.0

    def test_default_budget_when_missing(self, tmp_path):
        import json as _json
        p = tmp_path / "pricing.json"
        p.write_text(_json.dumps({"claude": {"models": {}}}))
        _, budget = load_pricing(p)
        assert budget == 25.0


def _make_event(ts: datetime, cost: float, model: str = "sonnet", session: str = "s1", skill: str = None) -> dict:
    return {
        "ts": ts,
        "cost_usd": cost,
        "model": model,
        "session_id": session,
        "skill_name": skill,
        "input_tokens": 1000,
        "output_tokens": 500,
        "cache_read_tokens": 0,
        "cache_creation_tokens": 0,
    }


class TestBuildWindow:
    def _now(self):
        return datetime(2026, 4, 28, 12, 0, 0, tzinfo=timezone.utc)

    def _cutoff(self, days=7):
        return self._now() - timedelta(days=days)

    def test_no_events_returns_empty_window(self):
        now = self._now()
        result = build_window([], self._cutoff(), 7, 25.0, now)
        assert result["spend_usd"] == 0.0
        assert result["session_rollups"]["session_count"] == 0

    def test_events_outside_window_excluded(self):
        now = self._now()
        old_event = _make_event(now - timedelta(days=10), 1.0)
        result = build_window([old_event], self._cutoff(days=7), 7, 25.0, now)
        assert result["spend_usd"] == 0.0

    def test_spend_sums_in_window(self):
        now = self._now()
        events = [
            _make_event(now - timedelta(days=1), 0.05),
            _make_event(now - timedelta(days=2), 0.10),
        ]
        result = build_window(events, self._cutoff(), 7, 25.0, now)
        assert abs(result["spend_usd"] - 0.15) < 1e-6

    def test_per_model_aggregation(self):
        now = self._now()
        events = [
            _make_event(now - timedelta(days=1), 0.10, model="opus"),
            _make_event(now - timedelta(days=1), 0.05, model="sonnet"),
        ]
        result = build_window(events, self._cutoff(), 7, 25.0, now)
        models = {m["model_id"] for m in result["per_model"]}
        assert "opus" in models
        assert "sonnet" in models

    def test_per_model_sorted_by_cost_desc(self):
        now = self._now()
        events = [
            _make_event(now - timedelta(days=1), 0.01, model="cheap"),
            _make_event(now - timedelta(days=1), 0.50, model="expensive"),
        ]
        result = build_window(events, self._cutoff(), 7, 25.0, now)
        assert result["per_model"][0]["model_id"] == "expensive"

    def test_session_rollup_count(self):
        now = self._now()
        events = [
            _make_event(now - timedelta(days=1), 0.05, session="s1"),
            _make_event(now - timedelta(days=1), 0.10, session="s2"),
            _make_event(now - timedelta(days=1), 0.02, session="s1"),
        ]
        result = build_window(events, self._cutoff(), 7, 25.0, now)
        assert result["session_rollups"]["session_count"] == 2

    def test_most_expensive_session(self):
        now = self._now()
        events = [
            _make_event(now - timedelta(days=1), 0.05, session="cheap"),
            _make_event(now - timedelta(days=1), 0.50, session="expensive"),
        ]
        result = build_window(events, self._cutoff(), 7, 25.0, now)
        assert result["session_rollups"]["most_expensive"]["session_id"] == "expensive"

    def test_skill_none_becomes_uncategorized(self):
        now = self._now()
        events = [_make_event(now - timedelta(days=1), 0.05, skill=None)]
        result = build_window(events, self._cutoff(), 7, 25.0, now)
        skill_names = {s["skill_name"] for s in result["per_skill"]}
        assert "uncategorized" in skill_names

    def test_share_pct_sums_to_100_single_model(self):
        now = self._now()
        events = [_make_event(now - timedelta(days=1), 0.10, model="opus")]
        result = build_window(events, self._cutoff(), 7, 25.0, now)
        total_pct = sum(m["share_pct"] for m in result["per_model"])
        assert total_pct == 100
