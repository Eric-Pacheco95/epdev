"""Tests for lib/file_lock -- locked_append and locked_read_modify_write."""
from __future__ import annotations

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from tools.scripts.lib.file_lock import locked_append, locked_read_modify_write


class TestLockedAppend:
    def test_creates_file_if_missing(self, tmp_path):
        p = tmp_path / "log.jsonl"
        locked_append(p, "line1")
        assert p.exists()
        assert "line1" in p.read_text()

    def test_appends_newline_if_missing(self, tmp_path):
        p = tmp_path / "log.jsonl"
        locked_append(p, "noeol")
        assert p.read_text().endswith(chr(10))

    def test_preserves_existing_newline(self, tmp_path):
        p = tmp_path / "log.jsonl"
        locked_append(p, "has_newline" + chr(10))
        content = p.read_text()
        assert content.count(chr(10)) == 1

    def test_multiple_appends_accumulate(self, tmp_path):
        p = tmp_path / "log.jsonl"
        locked_append(p, "first")
        locked_append(p, "second")
        content = p.read_text()
        assert "first" in content
        assert "second" in content

    def test_creates_parent_dirs(self, tmp_path):
        p = tmp_path / "subdir" / "nested" / "log.txt"
        locked_append(p, "x")
        assert p.exists()


class TestLockedReadModifyWrite:
    def test_creates_file_with_default(self, tmp_path):
        p = tmp_path / "state.json"
        result = locked_read_modify_write(p, lambda s: s, default={"count": 0})
        assert result == {"count": 0}
        assert p.exists()

    def test_mutator_applied_to_state(self, tmp_path):
        p = tmp_path / "state.json"
        locked_read_modify_write(p, lambda s: {**s, "x": 1})
        result = locked_read_modify_write(p, lambda s: {**s, "y": 2})
        assert result["x"] == 1
        assert result["y"] == 2

    def test_persists_across_calls(self, tmp_path):
        p = tmp_path / "state.json"
        locked_read_modify_write(p, lambda s: {"count": 42})
        result = locked_read_modify_write(p, lambda s: s)
        assert result["count"] == 42

    def test_non_dict_mutator_raises(self, tmp_path):
        p = tmp_path / "state.json"
        import pytest
        with pytest.raises(TypeError):
            locked_read_modify_write(p, lambda s: "not a dict")
