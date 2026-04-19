"""Tests for verify_backlog_health -- main() logic with monkeypatched BACKLOG path."""
from __future__ import annotations

import json
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

import tools.scripts.verify_backlog_health as vbh


def _make_backlog(tmp_path: Path, tasks: list[dict]) -> Path:
    bl = tmp_path / "task_backlog.jsonl"
    bl.write_text("\n".join(json.dumps(t) for t in tasks) + "\n", encoding="utf-8")
    return bl


def _run_main(monkeypatch, backlog: Path, max_age_days: int = 7) -> int:
    monkeypatch.setattr(vbh, "BACKLOG", backlog)
    import sys as _sys
    old_argv = _sys.argv
    _sys.argv = ["verify_backlog_health.py", "--max-age-days", str(max_age_days)]
    try:
        return vbh.main()
    except SystemExit as e:
        return int(e.code)
    finally:
        _sys.argv = old_argv


class TestVerifyBacklogHealth:
    def test_fail_when_backlog_missing(self, tmp_path, monkeypatch):
        code = _run_main(monkeypatch, tmp_path / "missing.jsonl")
        assert code == 1

    def test_pass_with_empty_backlog(self, tmp_path, monkeypatch):
        bl = tmp_path / "task_backlog.jsonl"
        bl.write_text("", encoding="utf-8")
        code = _run_main(monkeypatch, bl)
        assert code == 0

    def test_pass_with_fresh_pending_review(self, tmp_path, monkeypatch):
        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        tasks = [{"id": "T1", "status": "pending_review", "created": today, "description": "x"}]
        bl = _make_backlog(tmp_path, tasks)
        code = _run_main(monkeypatch, bl, max_age_days=7)
        assert code == 0

    def test_fail_with_stale_pending_review(self, tmp_path, monkeypatch):
        stale_date = (datetime.now(timezone.utc) - timedelta(days=10)).strftime("%Y-%m-%d")
        tasks = [{"id": "T2", "status": "pending_review", "created": stale_date, "description": "y"}]
        bl = _make_backlog(tmp_path, tasks)
        code = _run_main(monkeypatch, bl, max_age_days=7)
        assert code == 1

    def test_pass_with_only_done_tasks(self, tmp_path, monkeypatch):
        stale_date = (datetime.now(timezone.utc) - timedelta(days=30)).strftime("%Y-%m-%d")
        tasks = [{"id": "T3", "status": "done", "created": stale_date, "description": "z"}]
        bl = _make_backlog(tmp_path, tasks)
        code = _run_main(monkeypatch, bl)
        assert code == 0

    def test_skips_malformed_json_lines(self, tmp_path, monkeypatch):
        bl = tmp_path / "task_backlog.jsonl"
        bl.write_text('{"status": "done"}\nNOT_JSON\n{"status": "done"}\n', encoding="utf-8")
        code = _run_main(monkeypatch, bl)
        assert code == 0
