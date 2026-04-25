"""Tests for isc_producer.py -- is_already_checked and build_report edge cases."""
from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import patch

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

import tools.scripts.isc_producer as ip


class TestIsAlreadyChecked:
    def test_missing_file_returns_false(self, tmp_path, monkeypatch):
        monkeypatch.setattr(ip, "REPO_ROOT", tmp_path)
        result = ip.is_already_checked("nonexistent.md", "some criterion")
        assert result is False

    def test_empty_criterion_returns_false(self, tmp_path, monkeypatch):
        prd = tmp_path / "prd.md"
        prd.write_text("- [x] done criterion\n", encoding="utf-8")
        monkeypatch.setattr(ip, "REPO_ROOT", tmp_path)
        result = ip.is_already_checked("prd.md", "")
        assert result is False

    def test_checked_criterion_returns_true(self, tmp_path, monkeypatch):
        prd = tmp_path / "prd.md"
        prd.write_text("- [x] System starts successfully\n", encoding="utf-8")
        monkeypatch.setattr(ip, "REPO_ROOT", tmp_path)
        result = ip.is_already_checked("prd.md", "System starts successfully")
        assert result is True

    def test_unchecked_criterion_returns_false(self, tmp_path, monkeypatch):
        prd = tmp_path / "prd.md"
        prd.write_text("- [ ] System starts successfully\n", encoding="utf-8")
        monkeypatch.setattr(ip, "REPO_ROOT", tmp_path)
        result = ip.is_already_checked("prd.md", "System starts successfully")
        assert result is False

    def test_partial_match_unchecked_returns_false(self, tmp_path, monkeypatch):
        prd = tmp_path / "prd.md"
        prd.write_text("- [x] Something else\n- [ ] System starts\n", encoding="utf-8")
        monkeypatch.setattr(ip, "REPO_ROOT", tmp_path)
        result = ip.is_already_checked("prd.md", "System starts")
        assert result is False

    def test_multiple_lines_finds_checked(self, tmp_path, monkeypatch):
        prd = tmp_path / "prd.md"
        prd.write_text(
            "- [ ] Not done\n- [x] Done criterion\n- [ ] Also not done\n",
            encoding="utf-8",
        )
        monkeypatch.setattr(ip, "REPO_ROOT", tmp_path)
        result = ip.is_already_checked("prd.md", "Done criterion")
        assert result is True


class TestBuildReportExtras:
    def _make_prd_result(self, criteria=None, prd_path="test.md"):
        if criteria is None:
            criteria = []
        return {
            "prd_path": prd_path,
            "executor_output": {"criteria": criteria},
        }

    def test_timeout_hit_flag_preserved(self):
        report = ip.build_report([], 1.0, 0, timeout_hit=True)
        assert report["timeout_hit"] is True

    def test_timeout_hit_false_by_default(self):
        report = ip.build_report([], 1.0, 0)
        assert report["timeout_hit"] is False

    def test_prds_scanned_count(self):
        results = [self._make_prd_result() for _ in range(3)]
        report = ip.build_report(results, 1.0, 0)
        assert report["prds_scanned"] == 3

    def test_tasks_created_field(self):
        report = ip.build_report([], 1.0, 7)
        assert report["near_miss_tasks_created"] == 7

    def test_run_date_explicit(self):
        report = ip.build_report([], 1.0, 0, run_date="2026-04-25")
        assert report["run_date"] == "2026-04-25"

    def test_duration_rounded(self):
        report = ip.build_report([], 3.14159, 0)
        assert report["run_duration_s"] == 3.14

    def test_null_executor_output_counted_as_error(self):
        results = [{"prd_path": "prd.md", "executor_output": None}]
        report = ip.build_report(results, 1.0, 0)
        assert report["by_prd"][0]["status"] == "ERROR"

    def test_pass_criteria_tracked_in_ready_to_mark(self, tmp_path, monkeypatch):
        prd = tmp_path / "prd.md"
        prd.write_text("- [ ] some criterion\n", encoding="utf-8")
        monkeypatch.setattr(ip, "REPO_ROOT", tmp_path)
        results = [self._make_prd_result(
            prd_path="prd.md",
            criteria=[{"criterion": "some criterion", "verdict": "PASS", "evidence": "found"}]
        )]
        report = ip.build_report(results, 1.0, 0)
        rtm = report["ready_to_mark"]
        assert len(rtm) == 1
        assert rtm[0]["criterion"] == "some criterion"

    def test_already_checked_criterion_not_in_ready_to_mark(self, tmp_path, monkeypatch):
        prd = tmp_path / "prd.md"
        prd.write_text("- [x] already done\n", encoding="utf-8")
        monkeypatch.setattr(ip, "REPO_ROOT", tmp_path)
        results = [self._make_prd_result(
            prd_path="prd.md",
            criteria=[{"criterion": "already done", "verdict": "PASS", "evidence": "found"}]
        )]
        report = ip.build_report(results, 1.0, 0)
        assert report["ready_to_mark"] == []
