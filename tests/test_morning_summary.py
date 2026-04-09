"""Tests for morning_summary.py -- pure helper functions."""
from __future__ import annotations

import importlib.util
import json
from pathlib import Path

SCRIPT = Path(__file__).parents[1] / "tools" / "scripts" / "morning_summary.py"


def _load():
    spec = importlib.util.spec_from_file_location("morning_summary", SCRIPT)
    mod = importlib.util.module_from_spec(spec)  # type: ignore[arg-type]
    spec.loader.exec_module(mod)  # type: ignore[union-attr]
    return mod


class TestGetBacklogStatus:
    def test_returns_zeros_when_file_missing(self, tmp_path, monkeypatch):
        mod = _load()
        monkeypatch.setattr(mod, "BACKLOG_FILE", tmp_path / "missing.jsonl")
        result = mod.get_backlog_status()
        assert result == {"total": 0, "pending": 0, "done": 0, "failed": 0}

    def test_counts_status_correctly(self, tmp_path, monkeypatch):
        tasks = [
            {"id": "t1", "status": "pending"},
            {"id": "t2", "status": "pending"},
            {"id": "t3", "status": "done"},
            {"id": "t4", "status": "failed"},
        ]
        f = tmp_path / "backlog.jsonl"
        f.write_text("\n".join(json.dumps(t) for t in tasks), encoding="utf-8")
        mod = _load()
        monkeypatch.setattr(mod, "BACKLOG_FILE", f)
        result = mod.get_backlog_status()
        assert result["total"] == 4
        assert result["pending"] == 2
        assert result["done"] == 1
        assert result["failed"] == 1

    def test_handles_blank_lines(self, tmp_path, monkeypatch):
        f = tmp_path / "backlog.jsonl"
        f.write_text('\n{"id":"t1","status":"pending"}\n\n{"id":"t2","status":"done"}\n', encoding="utf-8")
        mod = _load()
        monkeypatch.setattr(mod, "BACKLOG_FILE", f)
        result = mod.get_backlog_status()
        assert result["total"] == 2

    def test_deferred_counted(self, tmp_path, monkeypatch):
        tasks = [
            {"id": "t1", "status": "deferred"},
            {"id": "t2", "status": "done"},
        ]
        f = tmp_path / "backlog.jsonl"
        f.write_text("\n".join(json.dumps(t) for t in tasks), encoding="utf-8")
        mod = _load()
        monkeypatch.setattr(mod, "BACKLOG_FILE", f)
        result = mod.get_backlog_status()
        assert result["deferred"] == 1


class TestGetOvernightSummary:
    def test_no_run_today_returns_message(self, tmp_path, monkeypatch):
        mod = _load()
        monkeypatch.setattr(mod, "OVERNIGHT_DIR", tmp_path)
        result = mod.get_overnight_summary()
        assert "no run today" in result

    def test_counts_md_files_when_dir_exists(self, tmp_path, monkeypatch):
        mod = _load()
        from datetime import datetime
        today = datetime.now().strftime("%Y-%m-%d")
        overnight_dir = tmp_path / f"overnight-{today}"
        overnight_dir.mkdir()
        (overnight_dir / "report.md").write_text("content")
        (overnight_dir / "signals.md").write_text("content")
        monkeypatch.setattr(mod, "OVERNIGHT_DIR", tmp_path)
        result = mod.get_overnight_summary()
        assert "2" in result
        assert "artifact" in result


class TestGetRecentDispatcherResults:
    def test_returns_empty_when_dir_missing(self, tmp_path, monkeypatch):
        mod = _load()
        monkeypatch.setattr(mod, "DISPATCHER_RUNS", tmp_path / "missing")
        result = mod.get_recent_dispatcher_results()
        assert result == []

    def test_returns_recent_json_files(self, tmp_path, monkeypatch):
        runs_dir = tmp_path / "runs"
        runs_dir.mkdir()
        report = {"task_id": "t1", "status": "done"}
        (runs_dir / "run1.json").write_text(json.dumps(report))
        mod = _load()
        monkeypatch.setattr(mod, "DISPATCHER_RUNS", runs_dir)
        result = mod.get_recent_dispatcher_results()
        assert len(result) == 1
        assert result[0]["task_id"] == "t1"

    def test_skips_non_json_files(self, tmp_path, monkeypatch):
        runs_dir = tmp_path / "runs"
        runs_dir.mkdir()
        (runs_dir / "run1.txt").write_text("not json")
        mod = _load()
        monkeypatch.setattr(mod, "DISPATCHER_RUNS", runs_dir)
        result = mod.get_recent_dispatcher_results()
        assert result == []
