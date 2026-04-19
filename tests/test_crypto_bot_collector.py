"""Tests for crypto_bot_collector._tail_file and _ascii_safe."""
from __future__ import annotations

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from tools.scripts.crypto_bot_collector import _tail_file, _ascii_safe


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
