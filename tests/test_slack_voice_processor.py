"""Tests for tools/scripts/slack_voice_processor.py I/O helpers."""

import json
from pathlib import Path
from unittest.mock import patch

import tools.scripts.slack_voice_processor as svp


class TestLoadState:
    def test_returns_empty_dict_when_file_missing(self, tmp_path):
        f = tmp_path / "state.json"
        with patch.object(svp, "STATE_FILE", f):
            result = svp._load_state()
        assert result == {}

    def test_loads_valid_state(self, tmp_path):
        f = tmp_path / "state.json"
        f.write_text(json.dumps({"voice:C123": "1234567890.000"}), encoding="utf-8")
        with patch.object(svp, "STATE_FILE", f):
            result = svp._load_state()
        assert result["voice:C123"] == "1234567890.000"

    def test_returns_empty_dict_on_invalid_json(self, tmp_path):
        f = tmp_path / "state.json"
        f.write_text("not valid json", encoding="utf-8")
        with patch.object(svp, "STATE_FILE", f):
            result = svp._load_state()
        assert result == {}


class TestSaveState:
    def test_writes_state_to_file(self, tmp_path):
        f = tmp_path / "state.json"
        state = {"voice:C456": "9876543210.000"}
        with patch.object(svp, "STATE_FILE", f):
            svp._save_state(state)
        loaded = json.loads(f.read_text(encoding="utf-8"))
        assert loaded["voice:C456"] == "9876543210.000"

    def test_creates_parent_directory(self, tmp_path):
        f = tmp_path / "subdir" / "state.json"
        with patch.object(svp, "STATE_FILE", f):
            svp._save_state({"key": "value"})
        assert f.exists()

    def test_atomic_write_via_tmp_file(self, tmp_path):
        f = tmp_path / "state.json"
        with patch.object(svp, "STATE_FILE", f):
            svp._save_state({"x": "1"})
        assert f.exists()
        assert not (tmp_path / "state.tmp").exists()

    def test_overwrites_existing_state(self, tmp_path):
        f = tmp_path / "state.json"
        f.write_text(json.dumps({"old": "value"}), encoding="utf-8")
        with patch.object(svp, "STATE_FILE", f):
            svp._save_state({"new": "value"})
        loaded = json.loads(f.read_text(encoding="utf-8"))
        assert "new" in loaded
        assert "old" not in loaded
