"""Tests for hook_post_compact.py -- _unchecked_items, _active_tasks, _incomplete_iscs."""
import sys
from pathlib import Path
from unittest.mock import patch

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

import tools.scripts.hook_post_compact as hpc
from tools.scripts.hook_post_compact import _unchecked_items, _active_tasks, _incomplete_iscs


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
        with patch.object(hpc, "TASKLIST", tmp_path / "missing.md"):
            result = _active_tasks()
        assert result == []

    def test_tasklist_with_unchecked(self, tmp_path):
        f = tmp_path / "tasklist.md"
        f.write_text("- [ ] Task A\n- [x] Done\n- [ ] Task B\n", encoding="utf-8")
        with patch.object(hpc, "TASKLIST", f):
            result = _active_tasks()
        assert result == ["Task A", "Task B"]

    def test_tasklist_all_checked_returns_empty(self, tmp_path):
        f = tmp_path / "tasklist.md"
        f.write_text("- [x] Done 1\n- [X] Done 2\n", encoding="utf-8")
        with patch.object(hpc, "TASKLIST", f):
            result = _active_tasks()
        assert result == []


class TestIncompleteIscs:
    def test_missing_work_dir_returns_empty(self, tmp_path):
        with patch.object(hpc, "WORK_DIR", tmp_path / "missing"):
            result = _incomplete_iscs()
        assert result == {}

    def test_empty_work_dir_returns_empty(self, tmp_path):
        work = tmp_path / "work"
        work.mkdir()
        with patch.object(hpc, "WORK_DIR", work):
            result = _incomplete_iscs()
        assert result == {}

    def test_prd_with_unchecked_included(self, tmp_path):
        work = tmp_path / "work"
        proj = work / "my-project"
        proj.mkdir(parents=True)
        (proj / "PRD.md").write_text("- [ ] Phase 1 criterion\n- [x] Done\n", encoding="utf-8")
        with patch.object(hpc, "WORK_DIR", work):
            result = _incomplete_iscs()
        assert "my-project" in result
        assert "Phase 1 criterion" in result["my-project"]

    def test_prd_all_checked_not_included(self, tmp_path):
        work = tmp_path / "work"
        proj = work / "done-project"
        proj.mkdir(parents=True)
        (proj / "PRD.md").write_text("- [x] Done\n", encoding="utf-8")
        with patch.object(hpc, "WORK_DIR", work):
            result = _incomplete_iscs()
        assert "done-project" not in result
