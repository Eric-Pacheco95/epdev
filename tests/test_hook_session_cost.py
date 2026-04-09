"""Tests for hook_session_cost.py -- token extraction and record building."""

import os
from unittest import mock

from tools.scripts.hook_session_cost import _extract_token_data, build_cost_record


def test_extract_token_data_empty():
    result = _extract_token_data({})
    assert result == {
        "cost_usd": None,
        "input_tokens": None,
        "output_tokens": None,
        "cache_read_tokens": None,
    }


def test_extract_token_data_from_payload():
    result = _extract_token_data({
        "input_tokens": 100,
        "output_tokens": 50,
        "cache_read_tokens": 25,
        "cost_usd": 0.0042,
    })
    assert result["input_tokens"] == 100
    assert result["output_tokens"] == 50
    assert result["cache_read_tokens"] == 25
    assert result["cost_usd"] == 0.0042


def test_extract_token_data_coerces_strings():
    result = _extract_token_data({"input_tokens": "200", "output_tokens": "100"})
    assert result["input_tokens"] == 200
    assert result["output_tokens"] == 100


def test_extract_token_data_ignores_invalid():
    result = _extract_token_data({"input_tokens": "not_a_number"})
    assert result["input_tokens"] is None


def test_extract_token_data_total_cost_fallback():
    result = _extract_token_data({"total_cost": "1.23"})
    assert result["cost_usd"] == 1.23


def test_extract_token_data_env_overrides(monkeypatch):
    monkeypatch.setenv("CLAUDE_SESSION_INPUT_TOKENS", "500")
    monkeypatch.setenv("CLAUDE_SESSION_OUTPUT_TOKENS", "250")
    monkeypatch.setenv("CLAUDE_SESSION_COST_USD", "0.05")
    result = _extract_token_data({})
    assert result["input_tokens"] == 500
    assert result["output_tokens"] == 250
    assert result["cost_usd"] == 0.05


def test_extract_token_data_payload_wins_over_env(monkeypatch):
    """Payload values take precedence over env vars."""
    monkeypatch.setenv("CLAUDE_SESSION_INPUT_TOKENS", "9999")
    result = _extract_token_data({"input_tokens": 100})
    assert result["input_tokens"] == 100


def test_build_cost_record_defaults():
    record = build_cost_record({})
    assert record["hook"] == "Stop"
    assert record["type"] == "session_cost"
    assert record["stop_reason"] == "end_turn"
    assert record["session_id"] == ""
    assert "note" in record  # no token data → note added


def test_build_cost_record_with_session():
    record = build_cost_record({"session_id": "sess-42", "stop_reason": "max_turns"})
    assert record["session_id"] == "sess-42"
    assert record["stop_reason"] == "max_turns"


def test_build_cost_record_no_note_when_data_present():
    record = build_cost_record({"input_tokens": 100, "output_tokens": 50})
    assert "note" not in record


def test_build_cost_record_ts_format():
    record = build_cost_record({})
    ts = record["ts"]
    # ISO-8601 UTC format: YYYY-MM-DDTHH:MM:SSZ
    assert len(ts) == 20
    assert ts.endswith("Z")
    assert ts[10] == "T"
