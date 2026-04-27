"""Tests for crypto_bot_collector._tail_file and _ascii_safe."""
from __future__ import annotations

import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

import tools.scripts.crypto_bot_collector as cbc_mod
from tools.scripts.crypto_bot_collector import (
    _tail_file, _ascii_safe,
    _load_dms_state, _save_dms_state, _read_jsonl_since,
)


class TestTailFile:
    def test_missing_file_returns_empty(self, tmp_path):
        assert _tail_file(tmp_path / "nonexistent.log") == []

    def test_empty_file_returns_empty(self, tmp_path):
        f = tmp_path / "empty.log"
        f.write_text("")
        assert _tail_file(f) == []

    def test_returns_last_n_lines(self, tmp_path):
        f = tmp_path / "data.log"
        f.write_text(chr(10).join([str(i) for i in range(20)]))
        result = _tail_file(f, n=5)
        assert len(result) == 5
        assert result[-1] == "19"

    def test_fewer_lines_than_n(self, tmp_path):
        f = tmp_path / "short.log"
        f.write_text("line1" + chr(10) + "line2")
        result = _tail_file(f, n=10)
        assert len(result) == 2

    def test_returns_list_of_strings(self, tmp_path):
        f = tmp_path / "data.log"
        f.write_text("a" + chr(10) + "b" + chr(10) + "c")
        result = _tail_file(f, n=3)
        assert all(isinstance(line, str) for line in result)


class TestAsciiSafeCollector:
    def test_plain_text_unchanged(self):
        assert _ascii_safe("hello world") == "hello world"

    def test_non_ascii_replaced(self):
        result = _ascii_safe("caf" + chr(233))
        assert "?" in result

    def test_empty_string_unchanged(self):
        assert _ascii_safe("") == ""


class TestLoadSaveDmsState:
    def test_missing_file_returns_defaults(self, tmp_path, monkeypatch):
        monkeypatch.setattr(cbc_mod, "DMS_STATE_FILE", tmp_path / "missing.json")
        monkeypatch.setattr(cbc_mod, "DATA_DIR", tmp_path)
        state = _load_dms_state()
        assert state["consecutive_failures"] == 0
        assert state["incident_active"] is False

    def test_roundtrip(self, tmp_path, monkeypatch):
        f = tmp_path / "dms.json"
        monkeypatch.setattr(cbc_mod, "DMS_STATE_FILE", f)
        monkeypatch.setattr(cbc_mod, "DATA_DIR", tmp_path)
        _save_dms_state({"consecutive_failures": 3, "incident_active": True, "alerts_sent": 1})
        result = _load_dms_state()
        assert result["consecutive_failures"] == 3
        assert result["incident_active"] is True

    def test_corrupt_file_returns_defaults(self, tmp_path, monkeypatch):
        f = tmp_path / "dms.json"
        f.write_text("broken{{{", encoding="utf-8")
        monkeypatch.setattr(cbc_mod, "DMS_STATE_FILE", f)
        monkeypatch.setattr(cbc_mod, "DATA_DIR", tmp_path)
        state = _load_dms_state()
        assert state["consecutive_failures"] == 0


class TestReadJsonlSince:
    def test_missing_file_returns_empty(self, tmp_path):
        entries, offset = _read_jsonl_since(tmp_path / "missing.jsonl", 0)
        assert entries == []
        assert offset == 0

    def test_reads_new_entries(self, tmp_path):
        f = tmp_path / "alerts.jsonl"
        f.write_text(json.dumps({"level": "warn"}) + "\n", encoding="utf-8")
        entries, new_offset = _read_jsonl_since(f, 0)
        assert len(entries) == 1
        assert entries[0]["level"] == "warn"

    def test_skips_already_read_content(self, tmp_path):
        f = tmp_path / "alerts.jsonl"
        line = json.dumps({"id": 1}) + "\n"
        f.write_text(line, encoding="utf-8")
        _, offset = _read_jsonl_since(f, 0)
        # Read again from current offset — should be empty
        entries, _ = _read_jsonl_since(f, offset)
        assert entries == []

    def test_skips_malformed_json_lines(self, tmp_path):
        f = tmp_path / "alerts.jsonl"
        f.write_text("not json\n" + json.dumps({"id": 2}) + "\n", encoding="utf-8")
        entries, _ = _read_jsonl_since(f, 0)
        assert len(entries) == 1
