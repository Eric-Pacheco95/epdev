"""Tests for hook_post_compact.py -- _unchecked_items, _active_tasks, _incomplete_iscs."""
import sys
from pathlib import Path
from unittest.mock import patch

import tools.scripts.hook_post_compact as hpc
from tools.scripts.hook_post_compact import _unchecked_items


def test_unchecked_items_basic():
    text = "- [ ] Do this\n- [x] Done\n- [ ] Do that\n"
    result = _unchecked_items(text)
    assert result == ["Do this", "Do that"]


def test_unchecked_items_empty():
    assert _unchecked_items("") == []


def test_unchecked_items_all_checked():
    text = "- [x] Done 1\n- [X] Done 2\n"
    assert _unchecked_items(text) == []


def test_unchecked_items_strips_whitespace():
    text = "- [ ]   Task with leading spaces  \n"
    result = _unchecked_items(text)
    assert result == ["Task with leading spaces"]


def test_unchecked_items_indented():
    text = "  - [ ] Indented task\n"
    result = _unchecked_items(text)
    assert result == ["Indented task"]


def test_unchecked_items_ignores_non_checkbox_lines():
    text = "# Header\nSome paragraph\n- [ ] Real task\n- Not a checkbox\n"
    result = _unchecked_items(text)
    assert result == ["Real task"]


class TestActiveTasks:
    def test_missing_tasklist_returns_empty(self, tmp_path):
        with patch.object(hpc, "TASKLIST", tmp_path / "tasklist.md"):
            result = hpc._active_tasks()
        assert result == []

    def test_reads_unchecked_from_tasklist(self, tmp_path):
        f = tmp_path / "tasklist.md"
        f.write_text("- [ ] Task A\n- [x] Done\n- [ ] Task B\n", encoding="utf-8")
        with patch.object(hpc, "TASKLIST", f):
            result = hpc._active_tasks()
        assert result == ["Task A", "Task B"]

    def test_all_checked_returns_empty(self, tmp_path):
        f = tmp_path / "tasklist.md"
        f.write_text("- [x] Done 1\n- [x] Done 2\n", encoding="utf-8")
        with patch.object(hpc, "TASKLIST", f):
            result = hpc._active_tasks()
        assert result == []


class TestIncompleteIscs:
    def test_missing_work_dir_returns_empty(self, tmp_path):
        with patch.object(hpc, "WORK_DIR", tmp_path / "nonexistent"):
            result = hpc._incomplete_iscs()
        assert result == {}

    def test_finds_unchecked_items_in_prd(self, tmp_path):
        proj = tmp_path / "myproject"
        proj.mkdir()
        (proj / "PRD.md").write_text("- [ ] ISC item 1\n- [x] Done\n", encoding="utf-8")
        with patch.object(hpc, "WORK_DIR", tmp_path):
            result = hpc._incomplete_iscs()
        assert "myproject" in result
        assert result["myproject"] == ["ISC item 1"]

    def test_fully_checked_prd_not_included(self, tmp_path):
        proj = tmp_path / "done_proj"
        proj.mkdir()
        (proj / "PRD.md").write_text("- [x] All done\n", encoding="utf-8")
        with patch.object(hpc, "WORK_DIR", tmp_path):
            result = hpc._incomplete_iscs()
        assert "done_proj" not in result

    def test_multiple_projects(self, tmp_path):
        for name in ["alpha", "beta"]:
            proj = tmp_path / name
            proj.mkdir()
            (proj / "PRD.md").write_text(f"- [ ] {name} task\n", encoding="utf-8")
        with patch.object(hpc, "WORK_DIR", tmp_path):
            result = hpc._incomplete_iscs()
        assert "alpha" in result
        assert "beta" in result
