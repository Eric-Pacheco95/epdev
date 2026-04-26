"""Tests for tools/scripts/lib/skill_launcher_lib.py pure functions."""

import json
from pathlib import Path

import pytest

from tools.scripts.lib.skill_launcher_lib import (
    parse_tokens_from_stream_json,
    estimate_cost_usd,
)

_DEFAULT_MODEL = "claude-sonnet-4-6"


class TestParseTokensFromStreamJson:
    def test_empty_text_returns_zeros(self):
        tokens, model = parse_tokens_from_stream_json("")
        assert tokens == 0
        assert model == _DEFAULT_MODEL

    def test_skips_malformed_lines(self):
        tokens, model = parse_tokens_from_stream_json("not json\n{bad")
        assert tokens == 0

    def test_sums_input_and_output_tokens(self):
        line = json.dumps({"usage": {"input_tokens": 100, "output_tokens": 50}})
        tokens, _ = parse_tokens_from_stream_json(line)
        assert tokens == 150

    def test_accumulates_multiple_lines(self):
        lines = [
            json.dumps({"usage": {"input_tokens": 100, "output_tokens": 50}}),
            json.dumps({"usage": {"input_tokens": 200, "output_tokens": 75}}),
        ]
        tokens, _ = parse_tokens_from_stream_json("\n".join(lines))
        assert tokens == 425

    def test_detects_model_from_message(self):
        line = json.dumps({"message": {"model": "claude-opus-4-7", "usage": {}}})
        _, model = parse_tokens_from_stream_json(line)
        assert model == "claude-opus-4-7"

    def test_detects_model_at_top_level(self):
        line = json.dumps({"model": "claude-haiku-4-5", "usage": {}})
        _, model = parse_tokens_from_stream_json(line)
        assert model == "claude-haiku-4-5"

    def test_ignores_blank_lines(self):
        text = "\n\n" + json.dumps({"usage": {"input_tokens": 10, "output_tokens": 5}}) + "\n\n"
        tokens, _ = parse_tokens_from_stream_json(text)
        assert tokens == 15

    def test_usage_inside_message_dict(self):
        line = json.dumps({"message": {"model": "claude-sonnet-4-6", "usage": {"input_tokens": 300, "output_tokens": 100}}})
        tokens, model = parse_tokens_from_stream_json(line)
        assert tokens == 400
        assert model == "claude-sonnet-4-6"


class TestEstimateCostUsd:
    def test_returns_float(self):
        result = estimate_cost_usd(1000, _DEFAULT_MODEL)
        assert isinstance(result, float)

    def test_zero_tokens_is_zero_cost(self):
        result = estimate_cost_usd(0, _DEFAULT_MODEL)
        assert result == 0.0

    def test_unknown_model_falls_back_to_zero(self):
        # Unknown model with no pricing file -> should not raise, returns 0.0
        result = estimate_cost_usd(100, "nonexistent-model-xyz")
        assert isinstance(result, float)
