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
