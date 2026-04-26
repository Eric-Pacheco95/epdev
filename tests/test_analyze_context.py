"""Tests for analyze_context pure functions."""
from __future__ import annotations

import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from tools.scripts.analyze_context import est_tokens, analyze


class TestEstTokens:
    def test_empty_string(self):
        assert est_tokens("") == 0

    def test_four_chars_is_one_token(self):
        assert est_tokens("abcd") == 1

    def test_eight_chars_is_two_tokens(self):
        assert est_tokens("abcdefgh") == 2

    def test_non_string_converted(self):
        result = est_tokens({"key": "val"})
        assert isinstance(result, int)
        assert result > 0

    def test_integer_input(self):
        result = est_tokens(12345)
        assert result == len("12345") // 4

    def test_floor_division(self):
        assert est_tokens("abc") == 0
        assert est_tokens("abcde") == 1


class TestAnalyze:
    def _write_jsonl(self, tmp_path, entries):
        p = tmp_path / "session.jsonl"
        with p.open("w", encoding="utf-8") as f:
            for e in entries:
                f.write(json.dumps(e) + "\n")
        return p

    def test_prints_file_header(self, tmp_path, capsys):
        p = self._write_jsonl(tmp_path, [{"type": "user", "message": {"role": "user", "content": "hello"}}])
        analyze(str(p))
        out = capsys.readouterr().out
        assert "session.jsonl" in out

    def test_prints_entry_count(self, tmp_path, capsys):
        entries = [
            {"type": "user", "message": {"role": "user", "content": "msg1"}},
            {"type": "assistant", "message": {"role": "assistant", "content": "resp1"}},
        ]
        p = self._write_jsonl(tmp_path, entries)
        analyze(str(p))
        out = capsys.readouterr().out
        assert "Entries: 2" in out

    def test_prints_total_row(self, tmp_path, capsys):
        p = self._write_jsonl(tmp_path, [{"type": "user", "message": {"role": "user", "content": "x" * 1000}}])
        analyze(str(p))
        out = capsys.readouterr().out
        assert "TOTAL" in out

    def test_skips_malformed_lines(self, tmp_path, capsys):
        p = tmp_path / "session.jsonl"
        p.write_text(
            '{"type": "user", "message": {"role": "user", "content": "valid"}}\n'
            'not valid json\n',
            encoding="utf-8",
        )
        analyze(str(p))
        out = capsys.readouterr().out
        assert "Entries: 1" in out
