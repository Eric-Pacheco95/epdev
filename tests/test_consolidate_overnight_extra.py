"""Tests for consolidate_overnight.py -- save_summary and get_dispatcher_reports."""
from __future__ import annotations

import json
import sys
from pathlib import Path
from unittest.mock import patch

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

import tools.scripts.consolidate_overnight as co


def _empty_merge_result():
    return {
        "merged": [],
        "conflicts": [],
        "review_branch": None,
        "status": "idle",
    }


class TestSaveSummary:
    def test_creates_json_and_md(self, tmp_path, monkeypatch):
        monkeypatch.setattr(co, "SUMMARY_DIR", tmp_path)
        json_path, md_path = co.save_summary([], _empty_merge_result(), [], "2026-04-25")
        assert json_path.exists()
        assert md_path.exists()

    def test_json_contains_date(self, tmp_path, monkeypatch):
        monkeypatch.setattr(co, "SUMMARY_DIR", tmp_path)
        json_path, _ = co.save_summary([], _empty_merge_result(), [], "2026-04-25")
        data = json.loads(json_path.read_text(encoding="utf-8"))
        assert data["date"] == "2026-04-25"

    def test_json_branch_counts(self, tmp_path, monkeypatch):
        monkeypatch.setattr(co, "SUMMARY_DIR", tmp_path)
        branches = [{"name": "jarvis/auto-T1"}, {"name": "jarvis/auto-T2"}]
        merged = [
            {"branch": "jarvis/auto-T1", "commits": 1, "files": []},
            {"branch": "jarvis/auto-T2", "commits": 2, "files": []},
        ]
        merge = {"merged": merged, "conflicts": [], "review_branch": "review/2026-04-25", "status": "ok"}
        json_path, _ = co.save_summary(branches, merge, [], "2026-04-25")
        data = json.loads(json_path.read_text(encoding="utf-8"))
        assert data["branches_found"] == 2
        assert data["branches_merged"] == 2

    def test_json_dispatcher_reports_summarized(self, tmp_path, monkeypatch):
        monkeypatch.setattr(co, "SUMMARY_DIR", tmp_path)
        reports = [
            {"task_id": "T1", "status": "done", "isc_passed": 3, "isc_total": 3},
        ]
        json_path, _ = co.save_summary([], _empty_merge_result(), reports, "2026-04-25")
        data = json.loads(json_path.read_text(encoding="utf-8"))
        assert len(data["dispatcher_reports"]) == 1
        assert data["dispatcher_reports"][0]["task_id"] == "T1"

    def test_md_file_is_nonempty(self, tmp_path, monkeypatch):
        monkeypatch.setattr(co, "SUMMARY_DIR", tmp_path)
        _, md_path = co.save_summary([], _empty_merge_result(), [], "2026-04-25")
        assert len(md_path.read_text(encoding="utf-8")) > 0

    def test_filenames_include_date(self, tmp_path, monkeypatch):
        monkeypatch.setattr(co, "SUMMARY_DIR", tmp_path)
        json_path, md_path = co.save_summary([], _empty_merge_result(), [], "2026-01-15")
        assert "2026-01-15" in json_path.name
        assert "2026-01-15" in md_path.name

    def test_review_branch_in_json(self, tmp_path, monkeypatch):
        monkeypatch.setattr(co, "SUMMARY_DIR", tmp_path)
        merge = dict(_empty_merge_result())
        merge["review_branch"] = "review/my-branch"
        json_path, _ = co.save_summary([], merge, [], "2026-04-25")
        data = json.loads(json_path.read_text(encoding="utf-8"))
        assert data["review_branch"] == "review/my-branch"


class TestGetDispatcherReports:
    def test_missing_report_dir_returns_empty(self, tmp_path, monkeypatch):
        monkeypatch.setattr(co, "REPO_ROOT", tmp_path)
        result = co.get_dispatcher_reports("2026-04-25")
        assert result == []

    def test_reads_matching_report(self, tmp_path, monkeypatch):
        monkeypatch.setattr(co, "REPO_ROOT", tmp_path)
        report_dir = tmp_path / "data" / "dispatcher_runs"
        report_dir.mkdir(parents=True)
        report_data = {"task_id": "T1", "status": "done", "date": "2026-04-25"}
        (report_dir / "task_T1_20260425_run.json").write_text(
            json.dumps(report_data), encoding="utf-8"
        )
        result = co.get_dispatcher_reports("2026-04-25")
        assert len(result) == 1
        assert result[0]["task_id"] == "T1"

    def test_ignores_different_date(self, tmp_path, monkeypatch):
        monkeypatch.setattr(co, "REPO_ROOT", tmp_path)
        report_dir = tmp_path / "data" / "dispatcher_runs"
        report_dir.mkdir(parents=True)
        (report_dir / "task_T1_20260424_run.json").write_text(
            json.dumps({"task_id": "T1", "date": "2026-04-24"}), encoding="utf-8"
        )
        result = co.get_dispatcher_reports("2026-04-25")
        assert result == []
