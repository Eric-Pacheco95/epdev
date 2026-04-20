"""Tests for backlog_archive functions."""

import json
import tempfile
from pathlib import Path
from datetime import datetime, timedelta

from tools.scripts.backlog_archive import (
    _read_jsonl,
    _write_jsonl_atomic,
    _append_jsonl,
    archive_tasks,
    NEVER_ARCHIVE,
)


def test_read_jsonl_nonexistent():
    assert _read_jsonl(Path("/nonexistent/file.jsonl")) == []


def test_read_jsonl_valid():
    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".jsonl", delete=False, dir=tempfile.gettempdir()
    ) as f:
        f.write('{"id": "t1", "status": "done"}\n')
        f.write('{"id": "t2", "status": "pending"}\n')
        f.flush()
        p = Path(f.name)

    tasks = _read_jsonl(p)
    assert len(tasks) == 2
    assert tasks[0]["id"] == "t1"
    p.unlink()


def test_write_jsonl_atomic():
    with tempfile.TemporaryDirectory() as tmpdir:
        path = Path(tmpdir) / "test.jsonl"
        tasks = [{"id": "t1"}, {"id": "t2"}]
        _write_jsonl_atomic(path, tasks)
        lines = path.read_text(encoding="utf-8").strip().split("\n")
        assert len(lines) == 2
        assert json.loads(lines[0])["id"] == "t1"


def test_archive_tasks_empty():
    with tempfile.TemporaryDirectory() as tmpdir:
        bp = Path(tmpdir) / "backlog.jsonl"
        ap = Path(tmpdir) / "archive.jsonl"
        count = archive_tasks(days=7, backlog_path=bp, archive_path=ap)
        assert count == 0


def test_archive_tasks_done_old():
    old_date = (datetime.now() - timedelta(days=30)).strftime("%Y-%m-%d")
    with tempfile.TemporaryDirectory() as tmpdir:
        bp = Path(tmpdir) / "backlog.jsonl"
        ap = Path(tmpdir) / "archive.jsonl"
        tasks = [
            {"id": "t1", "status": "done", "completed": old_date},
            {"id": "t2", "status": "pending"},
        ]
        bp.write_text("\n".join(json.dumps(t) for t in tasks) + "\n")

        count = archive_tasks(days=7, backlog_path=bp, archive_path=ap)
        assert count == 1

        remaining = [json.loads(l) for l in bp.read_text().strip().split("\n") if l.strip()]
        assert len(remaining) == 1
        assert remaining[0]["id"] == "t2"


def test_archive_tasks_done_recent():
    recent_date = datetime.now().strftime("%Y-%m-%d")
    with tempfile.TemporaryDirectory() as tmpdir:
        bp = Path(tmpdir) / "backlog.jsonl"
        ap = Path(tmpdir) / "archive.jsonl"
        tasks = [{"id": "t1", "status": "done", "completed": recent_date}]
        bp.write_text(json.dumps(tasks[0]) + "\n")

        count = archive_tasks(days=7, backlog_path=bp, archive_path=ap)
        assert count == 0


def test_archive_never_archive_status():
    old_date = (datetime.now() - timedelta(days=30)).strftime("%Y-%m-%d")
    with tempfile.TemporaryDirectory() as tmpdir:
        bp = Path(tmpdir) / "backlog.jsonl"
        ap = Path(tmpdir) / "archive.jsonl"
        tasks = [{"id": "t1", "status": "manual_review", "completed": old_date}]
        bp.write_text(json.dumps(tasks[0]) + "\n")

        count = archive_tasks(days=7, backlog_path=bp, archive_path=ap)
        assert count == 0


def test_archive_dry_run():
    old_date = (datetime.now() - timedelta(days=30)).strftime("%Y-%m-%d")
    with tempfile.TemporaryDirectory() as tmpdir:
        bp = Path(tmpdir) / "backlog.jsonl"
        ap = Path(tmpdir) / "archive.jsonl"
        tasks = [{"id": "t1", "status": "done", "completed": old_date}]
        bp.write_text(json.dumps(tasks[0]) + "\n")

        count = archive_tasks(days=7, dry_run=True, backlog_path=bp, archive_path=ap)
        assert count == 1
        # Original file unchanged in dry run
        remaining = [json.loads(l) for l in bp.read_text().strip().split("\n")]
        assert len(remaining) == 1


def test_archive_failed_old():
    old_date = (datetime.now() - timedelta(days=30)).strftime("%Y-%m-%d")
    with tempfile.TemporaryDirectory() as tmpdir:
        bp = Path(tmpdir) / "backlog.jsonl"
        ap = Path(tmpdir) / "archive.jsonl"
        tasks = [{"id": "t1", "status": "failed", "completed": old_date}]
        bp.write_text(json.dumps(tasks[0]) + "\n")

        count = archive_tasks(days=7, backlog_path=bp, archive_path=ap)
        assert count == 1


class TestAppendJsonl:
    def test_creates_file_if_missing(self, tmp_path):
        p = tmp_path / "sub" / "out.jsonl"
        _append_jsonl(p, [{"id": "1"}])
        assert p.exists()

    def test_appends_correct_lines(self, tmp_path):
        p = tmp_path / "out.jsonl"
        _append_jsonl(p, [{"a": 1}, {"b": 2}])
        lines = p.read_text().strip().splitlines()
        assert len(lines) == 2
        assert json.loads(lines[0]) == {"a": 1}
        assert json.loads(lines[1]) == {"b": 2}

    def test_appends_to_existing_file(self, tmp_path):
        p = tmp_path / "out.jsonl"
        p.write_text('{"x":0}\n')
        _append_jsonl(p, [{"y": 1}])
        lines = p.read_text().strip().splitlines()
        assert len(lines) == 2

    def test_empty_list_no_write(self, tmp_path):
        p = tmp_path / "out.jsonl"
        _append_jsonl(p, [])
        assert p.exists()
        assert p.read_text() == ""
