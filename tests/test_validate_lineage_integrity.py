"""Tests for compress_signals.validate_lineage_integrity."""
from __future__ import annotations

import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from tools.scripts.compress_signals import validate_lineage_integrity
import tools.scripts.compress_signals as cs


class TestValidateLineageIntegrity:
    def test_missing_file_returns_zeros(self, tmp_path, monkeypatch):
        monkeypatch.setattr(cs, "LINEAGE_FILE", tmp_path / "nonexistent.jsonl")
        assert validate_lineage_integrity() == (0, 0)

    def test_all_valid_jsonl(self, tmp_path, monkeypatch):
        f = tmp_path / "lineage.jsonl"
        f.write_text(
            json.dumps({"signal": "a.md"}) + chr(10)
            + json.dumps({"signal": "b.md"}) + chr(10)
        )
        monkeypatch.setattr(cs, "LINEAGE_FILE", f)
        valid, errors = validate_lineage_integrity()
        assert valid == 2
        assert errors == 0

    def test_invalid_json_line_counted_as_error(self, tmp_path, monkeypatch):
        f = tmp_path / "lineage.jsonl"
        f.write_text("not json" + chr(10) + json.dumps({"ok": 1}) + chr(10))
        monkeypatch.setattr(cs, "LINEAGE_FILE", f)
        valid, errors = validate_lineage_integrity()
        assert valid == 1
        assert errors == 1

    def test_blank_lines_skipped(self, tmp_path, monkeypatch):
        f = tmp_path / "lineage.jsonl"
        f.write_text(chr(10) + json.dumps({"x": 1}) + chr(10) + chr(10))
        monkeypatch.setattr(cs, "LINEAGE_FILE", f)
        valid, errors = validate_lineage_integrity()
        assert valid == 1
        assert errors == 0

    def test_mixed_valid_and_invalid(self, tmp_path, monkeypatch):
        lines = [
            json.dumps({"a": 1}),
            "BAD",
            json.dumps({"b": 2}),
            "ALSO BAD",
            json.dumps({"c": 3}),
        ]
        f = tmp_path / "lineage.jsonl"
        f.write_text(chr(10).join(lines) + chr(10))
        monkeypatch.setattr(cs, "LINEAGE_FILE", f)
        valid, errors = validate_lineage_integrity()
        assert valid == 3
        assert errors == 2
