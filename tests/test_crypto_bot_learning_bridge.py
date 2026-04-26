"""Tests for crypto_bot_learning_bridge._check_thresholds pure function."""
from __future__ import annotations

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

import json
from unittest.mock import patch

import tools.scripts.crypto_bot_learning_bridge as clb
from tools.scripts.crypto_bot_learning_bridge import (
    _check_thresholds,
    _ascii_safe,
)


class TestCheckThresholds:
    def test_no_change_returns_empty(self):
        current = {"win_rate": 55.0, "trade_count_closed": 10}
        last = {"win_rate": 55.0, "trade_count_closed": 10}
        assert _check_thresholds(current, last) == []

    def test_win_rate_delta_above_threshold(self):
        current = {"win_rate": 61.0}
        last = {"win_rate": 55.0}
        reasons = _check_thresholds(current, last)
        assert any("Win rate" in r for r in reasons)

    def test_win_rate_delta_below_threshold(self):
        current = {"win_rate": 56.0}
        last = {"win_rate": 55.0}
        reasons = _check_thresholds(current, last)
        assert not any("Win rate" in r for r in reasons)

    def test_trade_milestone_crossed(self):
        current = {"trade_count_closed": 50}
        last = {"trade_count_closed": 49}
        reasons = _check_thresholds(current, last)
        assert any("50" in r for r in reasons)

    def test_trade_milestone_already_passed(self):
        current = {"trade_count_closed": 51}
        last = {"trade_count_closed": 50}
        reasons = _check_thresholds(current, last)
        assert not any("50" in r for r in reasons)

    def test_empty_dicts_returns_empty(self):
        assert _check_thresholds({}, {}) == []

    def test_multiple_milestones_caught(self):
        current = {"trade_count_closed": 200}
        last = {"trade_count_closed": 0}
        reasons = _check_thresholds(current, last)
        # Milestones 50, 100, 200 should all fire
        assert len(reasons) >= 3


class TestAsciiSafe:
    def test_plain_ascii_unchanged(self):
        assert _ascii_safe("hello world") == "hello world"

    def test_unicode_replaced(self):
        result = _ascii_safe("café")
        assert "?" in result or result == "caf?"

    def test_empty_string(self):
        assert _ascii_safe("") == ""


class TestLoadState:
    def test_returns_empty_dict_when_file_missing(self, tmp_path):
        with patch.object(clb, "STATE_FILE", tmp_path / "state.json"):
            result = clb._load_state()
        assert result == {}

    def test_loads_valid_state(self, tmp_path):
        f = tmp_path / "state.json"
        f.write_text(json.dumps({"win_rate": 62.5}), encoding="utf-8")
        with patch.object(clb, "STATE_FILE", f):
            result = clb._load_state()
        assert result["win_rate"] == 62.5

    def test_returns_empty_on_invalid_json(self, tmp_path):
        f = tmp_path / "state.json"
        f.write_text("not json", encoding="utf-8")
        with patch.object(clb, "STATE_FILE", f):
            result = clb._load_state()
        assert result == {}
