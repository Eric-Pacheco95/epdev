"""Tests for crypto_bot_analysis_gate pure functions."""
from __future__ import annotations

import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from tools.scripts.crypto_bot_analysis_gate import _ascii_safe, check_gate
import tools.scripts.crypto_bot_analysis_gate as cag


class TestAsciiSafe:
    def test_plain_ascii_unchanged(self):
        assert _ascii_safe("hello") == "hello"

    def test_non_ascii_replaced(self):
        result = _ascii_safe("caf" + chr(233))
        assert "?" in result
        assert "caf" in result

    def test_empty_string(self):
        assert _ascii_safe("") == ""


class TestCheckGate:
    def test_missing_state_file_fails(self, tmp_path, monkeypatch):
        monkeypatch.setattr(cag, "STATE_FILE", tmp_path / "nonexistent.json")
        result = check_gate()
        assert result["passed"] is False
        assert result["closed_trades"] == 0

    def test_too_few_trades_fails(self, tmp_path, monkeypatch):
        state = tmp_path / "state.json"
        state.write_text(json.dumps({"trade_count_closed": 10}))
        monkeypatch.setattr(cag, "STATE_FILE", state)
        result = check_gate()
        assert result["passed"] is False
        assert result["closed_trades"] == 10

    def test_enough_trades_passes(self, tmp_path, monkeypatch):
        state = tmp_path / "state.json"
        state.write_text(json.dumps({"trade_count_closed": 50}))
        monkeypatch.setattr(cag, "STATE_FILE", state)
        result = check_gate()
        assert result["passed"] is True
        assert result["reason"] == ""

    def test_malformed_json_fails(self, tmp_path, monkeypatch):
        state = tmp_path / "state.json"
        state.write_text("NOT JSON")
        monkeypatch.setattr(cag, "STATE_FILE", state)
        result = check_gate()
        assert result["passed"] is False

    def test_more_than_minimum_passes(self, tmp_path, monkeypatch):
        state = tmp_path / "state.json"
        state.write_text(json.dumps({"trade_count_closed": 200}))
        monkeypatch.setattr(cag, "STATE_FILE", state)
        result = check_gate()
        assert result["passed"] is True
        assert result["closed_trades"] == 200
