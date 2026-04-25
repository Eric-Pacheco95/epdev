"""Tests for vitals_collector.py -- I/O helpers and memory tick functions."""
from __future__ import annotations

import json
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

import tools.scripts.vitals_collector as vc


class TestReadJson:
    def test_reads_valid_json(self, tmp_path):
        f = tmp_path / "data.json"
        f.write_text('{"key": "value"}', encoding="utf-8")
        assert vc._read_json(f) == {"key": "value"}

    def test_missing_file_returns_none(self, tmp_path):
        assert vc._read_json(tmp_path / "missing.json") is None

    def test_invalid_json_returns_none(self, tmp_path):
        f = tmp_path / "bad.json"
        f.write_text("not {{json}}", encoding="utf-8")
        assert vc._read_json(f) is None


class TestReadJsonlTail:
    def test_reads_last_n_entries(self, tmp_path):
        f = tmp_path / "log.jsonl"
        lines = [json.dumps({"i": i}) for i in range(10)]
        f.write_text("\n".join(lines), encoding="utf-8")
        result = vc._read_jsonl_tail(f, 3)
        assert len(result) == 3
        assert result[-1]["i"] == 9

    def test_missing_file_returns_empty(self, tmp_path):
        assert vc._read_jsonl_tail(tmp_path / "missing.jsonl") == []

    def test_skips_invalid_lines(self, tmp_path):
        f = tmp_path / "log.jsonl"
        f.write_text('{"a": 1}\nnot json\n{"b": 2}', encoding="utf-8")
        result = vc._read_jsonl_tail(f, 5)
        assert len(result) == 2

    def test_default_n_is_5(self, tmp_path):
        f = tmp_path / "log.jsonl"
        lines = [json.dumps({"i": i}) for i in range(10)]
        f.write_text("\n".join(lines), encoding="utf-8")
        assert len(vc._read_jsonl_tail(f)) == 5


class TestParseTs:
    def test_valid_z_timestamp(self):
        result = vc._parse_ts("2026-04-25T10:30:00Z")
        assert result is not None
        assert result.year == 2026

    def test_invalid_returns_none(self):
        assert vc._parse_ts("not-a-date") is None

    def test_empty_string_returns_none(self):
        assert vc._parse_ts("") is None

    def test_with_offset(self):
        result = vc._parse_ts("2026-01-01T00:00:00+05:00")
        assert result is not None


class TestLocalHourFromUtcIso:
    def test_none_input_returns_none(self):
        assert vc._local_hour_from_utc_iso(None) is None

    def test_empty_string_returns_none(self):
        assert vc._local_hour_from_utc_iso("") is None

    def test_invalid_string_returns_none(self):
        assert vc._local_hour_from_utc_iso("garbage") is None

    def test_valid_iso_returns_int(self):
        result = vc._local_hour_from_utc_iso("2026-04-25T14:00:00Z")
        assert isinstance(result, int)
        assert 0 <= result <= 23


class TestLoadMemoryTicks:
    def test_missing_file_returns_empty(self, tmp_path):
        result = vc.load_memory_ticks(tmp_path / "missing.jsonl", since_hours=24)
        assert result == []

    def test_returns_ticks_within_window(self, tmp_path):
        f = tmp_path / "ticks.jsonl"
        now = datetime.now(timezone.utc)
        recent = {"ts": (now - timedelta(hours=1)).strftime("%Y-%m-%dT%H:%M:%SZ"), "val": 1}
        old = {"ts": (now - timedelta(hours=48)).strftime("%Y-%m-%dT%H:%M:%SZ"), "val": 2}
        f.write_text(json.dumps(recent) + "\n" + json.dumps(old), encoding="utf-8")
        result = vc.load_memory_ticks(f, since_hours=24, now=now)
        assert len(result) == 1
        assert result[0]["val"] == 1

    def test_skips_invalid_json_lines(self, tmp_path):
        f = tmp_path / "ticks.jsonl"
        now = datetime.now(timezone.utc)
        valid = {"ts": (now - timedelta(hours=1)).strftime("%Y-%m-%dT%H:%M:%SZ"), "val": 1}
        f.write_text(json.dumps(valid) + "\nbad json line\n", encoding="utf-8")
        result = vc.load_memory_ticks(f, since_hours=24, now=now)
        assert len(result) == 1

    def test_empty_file_returns_empty(self, tmp_path):
        f = tmp_path / "ticks.jsonl"
        f.write_text("", encoding="utf-8")
        result = vc.load_memory_ticks(f, since_hours=24)
        assert result == []
