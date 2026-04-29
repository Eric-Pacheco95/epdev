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


class TestEmptyWindowExtended:
    def test_per_model_is_list(self):
        w = _empty_window(20.0)
        assert isinstance(w["per_model"], list)

    def test_per_skill_is_list(self):
        w = _empty_window(20.0)
        assert isinstance(w["per_skill"], list)

    def test_session_rollups_structure(self):
        w = _empty_window(20.0)
        rollups = w["session_rollups"]
        assert rollups["avg_usd"] == 0.0
        assert rollups["session_count"] == 0
        assert rollups["most_expensive"] is None

    def test_tokens_initialized_to_zero(self):
        w = _empty_window(20.0)
        assert w["input_tokens_total"] == 0
        assert w["output_tokens_total"] == 0
        assert w["cache_read_tokens_total"] == 0
        assert w["cache_creation_tokens_total"] == 0

    def test_spend_prev_window_zero(self):
        w = _empty_window(20.0)
        assert w["spend_prev_window_usd"] == 0.0


class TestComputeCostExtended:
    def test_cache_read_tokens(self):
        rates = {"input_per_mtok": 0, "output_per_mtok": 0,
                 "cache_read_per_mtok": 0.3, "cache_creation_per_mtok": 0}
        usage = {"cache_read_input_tokens": 1_000_000}
        result = compute_cost(usage, rates)
        assert result == pytest.approx(0.3)

    def test_cache_creation_tokens(self):
        rates = {"input_per_mtok": 0, "output_per_mtok": 0,
                 "cache_read_per_mtok": 0, "cache_creation_per_mtok": 3.75}
        usage = {"cache_creation_input_tokens": 1_000_000}
        result = compute_cost(usage, rates)
        assert result == pytest.approx(3.75)

    def test_all_zero_rates_returns_zero(self):
        rates = {"input_per_mtok": 0, "output_per_mtok": 0,
                 "cache_read_per_mtok": 0, "cache_creation_per_mtok": 0}
        usage = {"input_tokens": 1000, "output_tokens": 500}
        assert compute_cost(usage, rates) == 0.0
