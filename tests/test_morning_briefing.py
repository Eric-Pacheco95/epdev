"""Tests for tools/scripts/morning_briefing.py helper functions."""
from __future__ import annotations

import json
import sys
from collections import Counter
from pathlib import Path
from unittest.mock import patch

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

import tools.scripts.morning_briefing as mb


class TestBacklogCounts:
    def test_missing_file_returns_empty(self, tmp_path, monkeypatch):
        monkeypatch.setattr(mb, "BACKLOG", tmp_path / "missing.jsonl")
        counts, manual = mb._backlog_counts()
        assert counts == Counter()
        assert manual == []

    def test_counts_statuses(self, tmp_path, monkeypatch):
        backlog = tmp_path / "task_backlog.jsonl"
        tasks = [
            {"id": "t1", "status": "pending"},
            {"id": "t2", "status": "pending"},
            {"id": "t3", "status": "done"},
            {"id": "t4", "status": "manual_review", "description": "fix it"},
        ]
        backlog.write_text("\n".join(json.dumps(t) for t in tasks), encoding="utf-8")
        monkeypatch.setattr(mb, "BACKLOG", backlog)
        counts, manual = mb._backlog_counts()
        assert counts["pending"] == 2
        assert counts["done"] == 1
        assert counts["manual_review"] == 1
        assert len(manual) == 1

    def test_skips_blank_lines(self, tmp_path, monkeypatch):
        backlog = tmp_path / "task_backlog.jsonl"
        backlog.write_text(
            '{"id": "t1", "status": "pending"}\n\n\n{"id": "t2", "status": "done"}\n',
            encoding="utf-8",
        )
        monkeypatch.setattr(mb, "BACKLOG", backlog)
        counts, _ = mb._backlog_counts()
        assert counts["pending"] == 1
        assert counts["done"] == 1

    def test_skips_invalid_json(self, tmp_path, monkeypatch):
        backlog = tmp_path / "task_backlog.jsonl"
        backlog.write_text(
            '{"id": "t1", "status": "pending"}\nnot json at all\n',
            encoding="utf-8",
        )
        monkeypatch.setattr(mb, "BACKLOG", backlog)
        counts, _ = mb._backlog_counts()
        assert counts["pending"] == 1

    def test_missing_status_uses_unknown(self, tmp_path, monkeypatch):
        backlog = tmp_path / "task_backlog.jsonl"
        backlog.write_text('{"id": "t1"}\n', encoding="utf-8")
        monkeypatch.setattr(mb, "BACKLOG", backlog)
        counts, _ = mb._backlog_counts()
        assert counts["unknown"] == 1

    def test_manual_review_items_in_list(self, tmp_path, monkeypatch):
        backlog = tmp_path / "task_backlog.jsonl"
        tasks = [
            {"id": "m1", "status": "manual_review", "description": "check this"},
            {"id": "m2", "status": "manual_review", "description": "also this"},
            {"id": "t3", "status": "pending"},
        ]
        backlog.write_text("\n".join(json.dumps(t) for t in tasks), encoding="utf-8")
        monkeypatch.setattr(mb, "BACKLOG", backlog)
        counts, manual = mb._backlog_counts()
        assert len(manual) == 2
        assert manual[0]["id"] == "m1"


class TestGoalsExcerpt:
    def test_missing_goals_file_returns_fallback(self, tmp_path, monkeypatch):
        monkeypatch.setattr(mb, "GOALS", tmp_path / "missing_GOALS.md")
        result = mb._goals_excerpt()
        assert "not found" in result.lower() or "GOALS.md" in result

    def test_returns_up_to_max_lines(self, tmp_path, monkeypatch):
        goals = tmp_path / "GOALS.md"
        goals.write_text("\n".join(f"Line {i}" for i in range(50)), encoding="utf-8")
        monkeypatch.setattr(mb, "GOALS", goals)
        result = mb._goals_excerpt(max_lines=10)
        lines = result.splitlines()
        assert len(lines) == 10

    def test_returns_full_file_when_shorter_than_max(self, tmp_path, monkeypatch):
        goals = tmp_path / "GOALS.md"
        goals.write_text("Line 1\nLine 2\nLine 3\n", encoding="utf-8")
        monkeypatch.setattr(mb, "GOALS", goals)
        result = mb._goals_excerpt(max_lines=25)
        lines = [l for l in result.splitlines() if l]
        assert len(lines) == 3


class TestFinancialBlurb:
    def test_missing_snapshot_returns_message(self, tmp_path, monkeypatch):
        monkeypatch.setattr(mb, "SNAPSHOT", tmp_path / "missing.jsonl")
        result = mb._financial_blurb()
        assert "snapshot" in result.lower()

    def test_empty_snapshot_returns_message(self, tmp_path, monkeypatch):
        snap = tmp_path / "snapshot.jsonl"
        snap.write_text("", encoding="utf-8")
        monkeypatch.setattr(mb, "SNAPSHOT", snap)
        result = mb._financial_blurb()
        assert "empty" in result.lower() or "snapshot" in result.lower()

    def test_valid_snapshot_returns_ts(self, tmp_path, monkeypatch):
        snap = tmp_path / "snapshot.jsonl"
        row = {
            "ts": "2026-04-25T00:00:00Z",
            "crypto_bot": {"root_exists": True, "files": {"a": 1, "b": 2}},
        }
        snap.write_text(json.dumps(row) + "\n", encoding="utf-8")
        monkeypatch.setattr(mb, "SNAPSHOT", snap)
        result = mb._financial_blurb()
        assert "2026-04-25" in result

    def test_invalid_json_snapshot_returns_error(self, tmp_path, monkeypatch):
        snap = tmp_path / "snapshot.jsonl"
        snap.write_text("not json\n", encoding="utf-8")
        monkeypatch.setattr(mb, "SNAPSHOT", snap)
        result = mb._financial_blurb()
        assert "could not parse" in result or "parse" in result.lower() or "snapshot" in result.lower()
