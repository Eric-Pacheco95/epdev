"""Tests for branch_lifecycle.format_report and _load_backlog_index."""

import json
from pathlib import Path
import tools.scripts.branch_lifecycle as blc
from tools.scripts.branch_lifecycle import format_report, _load_backlog_index


def _make_branch(name, age_days, commit_count, diff_summary, is_stale=False, is_merged=False):
    return {
        "name": name,
        "age_days": age_days,
        "commit_count": commit_count,
        "diff_summary": diff_summary,
        "is_stale": is_stale,
        "is_merged": is_merged,
    }


def test_format_report_empty():
    result = format_report([])
    assert result == "No Jarvis autonomous branches found."


def test_format_report_active_branch():
    branch = _make_branch("jarvis/feature-x", 3, 2, "1 file changed")
    result = format_report([branch])
    assert "ACTIVE" in result
    assert "jarvis/feature-x" in result
    assert "3d old" in result


def test_format_report_stale_branch():
    branch = _make_branch("jarvis/old-feature", 10, 5, "3 files changed", is_stale=True)
    result = format_report([branch])
    assert "STALE" in result
    assert "jarvis/old-feature" in result
    assert "10d old" in result


def test_format_report_merged_branch():
    branch = _make_branch("jarvis/done", 15, 1, "2 files changed", is_merged=True)
    result = format_report([branch])
    assert "MERGED" in result
    assert "jarvis/done" in result


def test_format_report_totals_line():
    branches = [
        _make_branch("jarvis/active", 2, 1, "x"),
        _make_branch("jarvis/stale", 10, 3, "y", is_stale=True),
        _make_branch("jarvis/merged", 20, 1, "z", is_merged=True),
    ]
    result = format_report(branches)
    assert "Total: 3" in result
    assert "Stale: 1" in result
    assert "Merged: 1" in result
    assert "Active: 1" in result


def test_format_report_multiple_stale_sorted_by_age():
    branches = [
        _make_branch("jarvis/oldest", 30, 2, "x", is_stale=True),
        _make_branch("jarvis/newer", 8, 1, "y", is_stale=True),
    ]
    result = format_report(branches)
    idx_oldest = result.index("jarvis/oldest")
    idx_newer = result.index("jarvis/newer")
    assert idx_oldest < idx_newer  # oldest appears first (sorted descending by age)


# ── _load_backlog_index ──────────────────────────────────────────────

class TestLoadBacklogIndex:
    def test_missing_file_returns_empty(self, tmp_path, monkeypatch):
        monkeypatch.setattr(blc, "BACKLOG_FILE", tmp_path / "missing.jsonl")
        assert _load_backlog_index() == {}

    def test_empty_file_returns_empty(self, tmp_path, monkeypatch):
        f = tmp_path / "backlog.jsonl"
        f.write_text("", encoding="utf-8")
        monkeypatch.setattr(blc, "BACKLOG_FILE", f)
        assert _load_backlog_index() == {}

    def test_task_with_id_maps_auto_branch(self, tmp_path, monkeypatch):
        f = tmp_path / "backlog.jsonl"
        f.write_text(json.dumps({"id": "abc123", "status": "pending"}) + "\n", encoding="utf-8")
        monkeypatch.setattr(blc, "BACKLOG_FILE", f)
        idx = _load_backlog_index()
        assert "jarvis/auto-abc123" in idx

    def test_task_without_id_skipped(self, tmp_path, monkeypatch):
        f = tmp_path / "backlog.jsonl"
        f.write_text(json.dumps({"status": "pending"}) + "\n", encoding="utf-8")
        monkeypatch.setattr(blc, "BACKLOG_FILE", f)
        idx = _load_backlog_index()
        assert len(idx) == 0

    def test_task_with_branch_field_also_indexed(self, tmp_path, monkeypatch):
        f = tmp_path / "backlog.jsonl"
        task = {"id": "xyz", "branch": "jarvis/overnight-2026-04-07", "status": "done"}
        f.write_text(json.dumps(task) + "\n", encoding="utf-8")
        monkeypatch.setattr(blc, "BACKLOG_FILE", f)
        idx = _load_backlog_index()
        assert "jarvis/overnight-2026-04-07" in idx

    def test_malformed_json_skipped(self, tmp_path, monkeypatch):
        f = tmp_path / "backlog.jsonl"
        f.write_text('not json\n{"id": "ok1"}\n', encoding="utf-8")
        monkeypatch.setattr(blc, "BACKLOG_FILE", f)
        idx = _load_backlog_index()
        assert "jarvis/auto-ok1" in idx
        assert len(idx) == 1
