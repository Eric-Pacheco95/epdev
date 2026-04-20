"""Tests for costs_aggregator.py -- pure helper functions."""
import pytest
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from tools.scripts.costs_aggregator import compute_cost, extract_text


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
