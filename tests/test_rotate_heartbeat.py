"""Tests for rotate_heartbeat pure functions."""

import json
import tempfile
from datetime import datetime, timezone
from pathlib import Path

from tools.scripts.rotate_heartbeat import (
    load_retention_days,
    parse_entries,
    partition_entries,
    aggregate_monthly,
)


def test_load_retention_days_default():
    assert load_retention_days(Path("/nonexistent/config.json")) == 30


def test_load_retention_days_from_config():
    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".json", delete=False, dir=tempfile.gettempdir()
    ) as f:
        json.dump({"retention": {"rollup_after_days": 14}}, f)
        f.flush()
        p = Path(f.name)
    assert load_retention_days(p) == 14
    p.unlink()


def test_parse_entries_empty():
    assert parse_entries(Path("/nonexistent/history.jsonl")) == []


def test_parse_entries_valid():
    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".jsonl", delete=False, dir=tempfile.gettempdir()
    ) as f:
        f.write('{"ts": "2026-03-28T10:00:00Z", "metrics": {}}\n')
        f.write('bad json\n')
        f.write('{"ts": "2026-03-29T10:00:00Z", "metrics": {}}\n')
        f.flush()
        p = Path(f.name)
    entries = parse_entries(p)
    assert len(entries) == 2  # skips bad line
    p.unlink()


def test_partition_entries_split():
    entries = [
        {"ts": "2026-03-28T10:00:00Z"},
        {"ts": "2026-01-15T10:00:00Z"},
        {"ts": "2026-03-30T10:00:00Z"},
    ]
    cutoff = datetime(2026, 3, 1, tzinfo=timezone.utc)
    recent, old = partition_entries(entries, cutoff)
    assert len(recent) == 2
    assert len(old) == 1


def test_partition_entries_bad_ts():
    entries = [{"ts": "not-a-timestamp"}]
    cutoff = datetime(2026, 3, 1, tzinfo=timezone.utc)
    recent, old = partition_entries(entries, cutoff)
    assert len(recent) == 1  # unparseable kept in recent
    assert len(old) == 0


def test_aggregate_monthly_basic():
    entries = [
        {"ts": "2026-01-15T10:00:00Z", "metrics": {"cpu": {"value": 50}}},
        {"ts": "2026-01-20T10:00:00Z", "metrics": {"cpu": {"value": 70}}},
        {"ts": "2026-02-10T10:00:00Z", "metrics": {"cpu": {"value": 30}}},
    ]
    summaries = aggregate_monthly(entries)
    assert "2026-01" in summaries
    assert "2026-02" in summaries
    jan = summaries["2026-01"]["metrics"]["cpu"]
    assert jan["min"] == 50.0
    assert jan["max"] == 70.0
    assert jan["avg"] == 60.0
    assert jan["samples"] == 2


def test_aggregate_monthly_empty():
    assert aggregate_monthly([]) == {}


def test_aggregate_monthly_bad_ts():
    entries = [{"ts": "bad", "metrics": {"cpu": {"value": 50}}}]
    assert aggregate_monthly(entries) == {}
