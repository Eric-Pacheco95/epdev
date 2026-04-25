"""Tests for quality_gate_check.py -- check_file_exists and cross_ref_decisions."""
from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import patch

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

import tools.scripts.quality_gate_check as qgc


class TestCheckFileExists:
    def test_existing_file_returns_true(self, tmp_path, monkeypatch):
        f = tmp_path / "report.md"
        f.write_text("content", encoding="utf-8")
        monkeypatch.setattr(qgc, "REPO_ROOT", tmp_path)
        ref, found = qgc.check_file_exists("report.md")
        assert found is True
        assert ref == "report.md"

    def test_missing_file_returns_false(self, tmp_path, monkeypatch):
        monkeypatch.setattr(qgc, "REPO_ROOT", tmp_path)
        ref, found = qgc.check_file_exists("missing.md")
        assert found is False
        assert ref == "missing.md"

    def test_leading_slash_stripped(self, tmp_path, monkeypatch):
        f = tmp_path / "data.md"
        f.write_text("hi", encoding="utf-8")
        monkeypatch.setattr(qgc, "REPO_ROOT", tmp_path)
        _, found = qgc.check_file_exists("/data.md")
        assert found is True

    def test_tilde_prefix_stripped(self, tmp_path, monkeypatch):
        f = tmp_path / "notes.md"
        f.write_text("hi", encoding="utf-8")
        monkeypatch.setattr(qgc, "REPO_ROOT", tmp_path)
        _, found = qgc.check_file_exists("~/notes.md")
        assert found is True


class TestCrossRefDecisions:
    def _make_task(self, title, description="", checked=False):
        return {"raw_title": title, "description": description, "checked": checked}

    def _make_decision(self, topic, file="decisions/test.md"):
        return {"topic": topic, "file": file}

    def test_empty_inputs(self):
        result = qgc.cross_ref_decisions([], [])
        assert result == []

    def test_no_decisions(self):
        tasks = [self._make_task("Deploy new feature")]
        result = qgc.cross_ref_decisions(tasks, [])
        assert len(result) == 1
        assert result[0]["has_decision"] is False

    def test_matching_decision_detected(self):
        tasks = [self._make_task("implement authentication system")]
        decisions = [self._make_decision("authentication system implementation")]
        result = qgc.cross_ref_decisions(tasks, decisions)
        assert result[0]["has_decision"] is True

    def test_no_overlap_not_matched(self):
        tasks = [self._make_task("fix login bug")]
        decisions = [self._make_decision("crypto trading strategy")]
        result = qgc.cross_ref_decisions(tasks, decisions)
        assert result[0]["has_decision"] is False

    def test_checked_status_preserved(self):
        tasks = [self._make_task("test task", checked=True)]
        result = qgc.cross_ref_decisions(tasks, [])
        assert result[0]["checked"] is True

    def test_task_title_preserved(self):
        tasks = [self._make_task("My Task Title")]
        result = qgc.cross_ref_decisions(tasks, [])
        assert result[0]["task"] == "My Task Title"

    def test_description_searched_too(self):
        tasks = [self._make_task("simple task", description="deploy production release system")]
        decisions = [self._make_decision("production release deployment system")]
        result = qgc.cross_ref_decisions(tasks, decisions)
        assert result[0]["has_decision"] is True

    def test_decision_file_referenced(self):
        tasks = [self._make_task("implement authentication system")]
        decisions = [self._make_decision("authentication system", "history/decisions/auth.md")]
        result = qgc.cross_ref_decisions(tasks, decisions)
        assert "history/decisions/auth.md" in result[0]["decisions"]

    def test_short_words_ignored(self):
        tasks = [self._make_task("do fix it")]
        decisions = [self._make_decision("do fix it")]
        result = qgc.cross_ref_decisions(tasks, decisions)
        assert result[0]["has_decision"] is False
