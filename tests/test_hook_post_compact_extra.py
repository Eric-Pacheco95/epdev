"""Tests for hook_post_compact.py -- _active_tasks and _incomplete_iscs."""
from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import patch

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

import tools.scripts.hook_post_compact as hpc


class TestActiveTasks:
    def test_missing_tasklist_returns_empty(self, tmp_path, monkeypatch):
        monkeypatch.setattr(hpc, "TASKLIST", tmp_path / "missing.md")
        result = hpc._active_tasks()
        assert result == []

    def test_returns_unchecked_items(self, tmp_path, monkeypatch):
        tasklist = tmp_path / "tasklist.md"
        tasklist.write_text(
            "- [ ] Task one\n- [x] Task done\n- [ ] Task two\n",
            encoding="utf-8",
        )
        monkeypatch.setattr(hpc, "TASKLIST", tasklist)
        result = hpc._active_tasks()
        assert "Task one" in result
        assert "Task two" in result
        assert "Task done" not in result

    def test_empty_file_returns_empty(self, tmp_path, monkeypatch):
        tasklist = tmp_path / "tasklist.md"
        tasklist.write_text("", encoding="utf-8")
        monkeypatch.setattr(hpc, "TASKLIST", tasklist)
        result = hpc._active_tasks()
        assert result == []

    def test_all_checked_returns_empty(self, tmp_path, monkeypatch):
        tasklist = tmp_path / "tasklist.md"
        tasklist.write_text("- [x] Done\n- [x] Also done\n", encoding="utf-8")
        monkeypatch.setattr(hpc, "TASKLIST", tasklist)
        result = hpc._active_tasks()
        assert result == []


class TestIncompleteIscs:
    def test_missing_work_dir_returns_empty(self, tmp_path, monkeypatch):
        monkeypatch.setattr(hpc, "WORK_DIR", tmp_path / "missing_dir")
        result = hpc._incomplete_iscs()
        assert result == {}

    def test_no_prd_files_returns_empty(self, tmp_path, monkeypatch):
        work_dir = tmp_path / "work"
        work_dir.mkdir()
        monkeypatch.setattr(hpc, "WORK_DIR", work_dir)
        result = hpc._incomplete_iscs()
        assert result == {}

    def test_prd_with_unchecked_items(self, tmp_path, monkeypatch):
        work_dir = tmp_path / "work"
        project_dir = work_dir / "my-project"
        project_dir.mkdir(parents=True)
        prd = project_dir / "PRD.md"
        prd.write_text("- [ ] Criterion A\n- [ ] Criterion B\n", encoding="utf-8")
        monkeypatch.setattr(hpc, "WORK_DIR", work_dir)
        result = hpc._incomplete_iscs()
        assert "my-project" in result
        assert len(result["my-project"]) == 2

    def test_prd_all_checked_not_included(self, tmp_path, monkeypatch):
        work_dir = tmp_path / "work"
        project_dir = work_dir / "done-project"
        project_dir.mkdir(parents=True)
        prd = project_dir / "PRD.md"
        prd.write_text("- [x] All done\n- [x] Also done\n", encoding="utf-8")
        monkeypatch.setattr(hpc, "WORK_DIR", work_dir)
        result = hpc._incomplete_iscs()
        assert "done-project" not in result

    def test_multiple_projects(self, tmp_path, monkeypatch):
        work_dir = tmp_path / "work"
        for proj in ["proj-a", "proj-b"]:
            d = work_dir / proj
            d.mkdir(parents=True)
            (d / "PRD.md").write_text(f"- [ ] {proj} task\n", encoding="utf-8")
        monkeypatch.setattr(hpc, "WORK_DIR", work_dir)
        result = hpc._incomplete_iscs()
        assert "proj-a" in result
        assert "proj-b" in result

    def test_project_name_from_parent_dir(self, tmp_path, monkeypatch):
        work_dir = tmp_path / "work"
        project_dir = work_dir / "specific-project"
        project_dir.mkdir(parents=True)
        prd = project_dir / "PRD.md"
        prd.write_text("- [ ] Item\n", encoding="utf-8")
        monkeypatch.setattr(hpc, "WORK_DIR", work_dir)
        result = hpc._incomplete_iscs()
        assert "specific-project" in result
