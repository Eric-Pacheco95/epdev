"""Tests for backlog_dashboard pure functions."""

import json
import tempfile
from pathlib import Path
from datetime import datetime

from tools.scripts.backlog_dashboard import (
    load_backlog,
    count_archive,
    parse_date,
    bucket_tasks,
    compute_stats,
    load_execution_time,
    ALL_STATUSES,
)


def test_load_backlog_nonexistent():
    assert load_backlog("/nonexistent/path.jsonl") == []


def test_load_backlog_valid():
    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".jsonl", delete=False, dir=tempfile.gettempdir()
    ) as f:
        f.write('{"id": "t1", "status": "done"}\n')
        f.write('{"id": "t2", "status": "pending"}\n')
        f.flush()
        p = Path(f.name)

    tasks = load_backlog(p)
    assert len(tasks) == 2
    p.unlink()


def test_load_backlog_bad_json():
    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".jsonl", delete=False, dir=tempfile.gettempdir()
    ) as f:
        f.write('{"id": "t1"}\n')
        f.write('not json\n')
        f.write('{"id": "t2"}\n')
        f.flush()
        p = Path(f.name)

    tasks = load_backlog(p)
    assert len(tasks) == 2  # skips bad line
    p.unlink()


def test_count_archive_nonexistent():
    assert count_archive("/nonexistent/archive.jsonl") == 0


def test_count_archive_valid():
    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".jsonl", delete=False, dir=tempfile.gettempdir()
    ) as f:
        f.write('{"id": "t1"}\n{"id": "t2"}\n')
        f.flush()
        p = Path(f.name)

    assert count_archive(p) == 2
    p.unlink()


def test_parse_date_iso():
    d = parse_date("2026-03-28")
    assert d is not None
    assert d.year == 2026
    assert d.month == 3
    assert d.day == 28


def test_parse_date_timestamp():
    d = parse_date("2026-03-28T10:30:00")
    assert d is not None
    assert d.day == 28


def test_parse_date_none():
    assert parse_date(None) is None
    assert parse_date("") is None


def test_parse_date_invalid():
    assert parse_date("not-a-date") is None


def test_bucket_tasks_basic():
    tasks = [
        {"id": "t1", "status": "done"},
        {"id": "t2", "status": "pending"},
        {"id": "t3", "status": "done"},
        {"id": "t4", "status": "executing"},
    ]
    buckets = bucket_tasks(tasks)
    assert len(buckets["done"]) == 2
    assert len(buckets["pending"]) == 1
    assert len(buckets["executing"]) == 1


def test_bucket_tasks_unknown_status():
    tasks = [{"id": "t1", "status": "weird_status"}]
    buckets = bucket_tasks(tasks)
    assert len(buckets["pending"]) == 1  # unknown -> pending


def test_bucket_tasks_empty():
    buckets = bucket_tasks([])
    for status in ALL_STATUSES:
        assert buckets[status] == []


class TestComputeStats:
    def _recent_date(self):
        from datetime import datetime, timedelta
        return (datetime.now() - timedelta(days=3)).strftime("%Y-%m-%d")

    def test_empty_tasks(self):
        stats = compute_stats([])
        assert stats["success_rate_14d"] == 1.0
        assert stats["tasks_completed_14d"] == 0
        assert stats["tasks_failed_14d"] == 0
        assert stats["pending_count"] == 0

    def test_counts_done_tasks_within_14d(self):
        tasks = [{"status": "done", "completed": self._recent_date()}]
        stats = compute_stats(tasks)
        assert stats["tasks_completed_14d"] == 1

    def test_counts_failed_tasks_within_14d(self):
        tasks = [{"status": "failed", "completed": self._recent_date()}]
        stats = compute_stats(tasks)
        assert stats["tasks_failed_14d"] == 1
        assert stats["success_rate_14d"] == 0.0

    def test_success_rate_mixed(self):
        recent = self._recent_date()
        tasks = [
            {"status": "done", "completed": recent},
            {"status": "done", "completed": recent},
            {"status": "failed", "completed": recent},
        ]
        stats = compute_stats(tasks)
        assert abs(stats["success_rate_14d"] - 2/3) < 0.01

    def test_pending_count(self):
        tasks = [{"status": "pending"}, {"status": "pending"}, {"status": "done"}]
        stats = compute_stats(tasks)
        assert stats["pending_count"] == 2

    def test_old_done_not_counted(self):
        old_date = "2020-01-01"
        tasks = [{"status": "done", "completed": old_date}]
        stats = compute_stats(tasks)
        assert stats["tasks_completed_14d"] == 0


class TestLoadExecutionTime:
    def test_returns_none_for_none_path(self):
        assert load_execution_time(None) is None

    def test_returns_none_for_missing_file(self, tmp_path):
        assert load_execution_time(str(tmp_path / "nonexistent.json")) is None

    def test_reads_elapsed_min(self, tmp_path):
        f = tmp_path / "report.json"
        f.write_text(json.dumps({"elapsed_min": 7.5}), encoding="utf-8")
        assert load_execution_time(str(f)) == 7.5

    def test_reads_elapsed_sec_and_converts(self, tmp_path):
        f = tmp_path / "report.json"
        f.write_text(json.dumps({"elapsed_sec": 120}), encoding="utf-8")
        assert load_execution_time(str(f)) == 2.0

    def test_reads_duration_minutes(self, tmp_path):
        f = tmp_path / "report.json"
        f.write_text(json.dumps({"duration_minutes": 5}), encoding="utf-8")
        assert load_execution_time(str(f)) == 5.0

    def test_reads_elapsed_seconds(self, tmp_path):
        f = tmp_path / "report.json"
        f.write_text(json.dumps({"elapsed_seconds": 90}), encoding="utf-8")
        assert load_execution_time(str(f)) == 1.5

    def test_returns_none_when_no_time_key(self, tmp_path):
        f = tmp_path / "report.json"
        f.write_text(json.dumps({"status": "done"}), encoding="utf-8")
        assert load_execution_time(str(f)) is None

    def test_returns_none_for_invalid_json(self, tmp_path):
        f = tmp_path / "report.json"
        f.write_text("not valid", encoding="utf-8")
        assert load_execution_time(str(f)) is None
