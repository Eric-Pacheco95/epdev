"""Tests for collectors.core miscellaneous functions."""

import json
import os
import tempfile
from datetime import timezone
from pathlib import Path
from tools.scripts.collectors.core import (
    _dir_size_mb, _parse_datetime_utc, reset_query_cache, _query_events_cache,
    COLLECTOR_TYPES, collect_hook_output_size, collect_json_field,
)


def test_dir_size_mb_empty():
    with tempfile.TemporaryDirectory() as tmpdir:
        assert _dir_size_mb(Path(tmpdir)) == 0.0


def test_dir_size_mb_with_files():
    with tempfile.TemporaryDirectory() as tmpdir:
        # Write 100KB to avoid rounding to 0.00
        with open(os.path.join(tmpdir, "a.txt"), "wb") as f:
            f.write(b"x" * (100 * 1024))
        size = _dir_size_mb(Path(tmpdir))
    assert size > 0.05
    assert size < 0.2


def test_dir_size_mb_nested():
    with tempfile.TemporaryDirectory() as tmpdir:
        sub = os.path.join(tmpdir, "sub")
        os.makedirs(sub)
        with open(os.path.join(sub, "big.bin"), "wb") as f:
            f.write(b"x" * (1024 * 1024))  # 1MB
        size = _dir_size_mb(Path(tmpdir))
    assert 0.9 < size < 1.1


def test_reset_query_cache():
    import tools.scripts.collectors.core as mod
    mod._query_events_cache = {"fake": "data"}
    mod._backlog_health_cache = [{"fake": "metric"}]
    reset_query_cache()
    assert mod._query_events_cache is None
    assert mod._backlog_health_cache is None


def test_collector_types_registry():
    """Verify all expected collector types are registered."""
    expected = {
        "file_count", "file_count_velocity", "checkbox_count",
        "checkbox_delta", "prd_checkbox", "derived", "query_events",
        "file_recency", "dir_count", "disk_usage", "hook_output_size",
        "scheduled_tasks", "auth_health", "signal_volume",
        "manifest_signal_count", "manifest_signal_velocity",
        "autonomous_signal_rate", "manifest_autonomous_signal_rate",
        "producer_health", "producer_recency", "backlog_health_metric", "system_resources",
        "stale_branches", "learning_retention", "json_field",
    }
    assert set(COLLECTOR_TYPES.keys()) == expected


def test_hook_output_size_missing_script():
    cfg = {"name": "test_hook", "hook_script": "nonexistent/hook.py"}
    result = collect_hook_output_size(cfg, Path("/tmp"))
    assert result["value"] is None


def test_hook_output_size_no_config():
    cfg = {"name": "test_hook"}
    result = collect_hook_output_size(cfg, Path("/tmp"))
    assert result["value"] is None
    assert "no hook_script" in result["detail"]


class TestCollectJsonField:
    def test_basic_read(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "data.json"
            p.write_text(json.dumps({"count": 42}))
            result = collect_json_field({"name": "m", "path": str(p), "field": "count"}, Path(d))
        assert result["value"] == 42

    def test_nested_dotted_path(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "data.json"
            p.write_text(json.dumps({"a": {"b": {"c": 3.14}}}))
            result = collect_json_field({"name": "m", "path": str(p), "field": "a.b.c"}, Path(d))
        assert result["value"] == 3.14

    def test_missing_file(self):
        with tempfile.TemporaryDirectory() as d:
            result = collect_json_field({"name": "m", "path": "missing.json", "field": "x"}, Path(d))
        assert result["value"] is None
        assert "not found" in result["detail"]

    def test_missing_key(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "data.json"
            p.write_text(json.dumps({"a": 1}))
            result = collect_json_field({"name": "m", "path": str(p), "field": "b"}, Path(d))
        assert result["value"] is None
        assert "not found" in result["detail"]

    def test_non_numeric_value(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "data.json"
            p.write_text(json.dumps({"label": "hello"}))
            result = collect_json_field({"name": "m", "path": str(p), "field": "label"}, Path(d))
        assert result["value"] is None
        assert "not numeric" in result["detail"]

    def test_no_field_config(self):
        result = collect_json_field({"name": "m", "path": "/some/file.json"}, Path("/tmp"))
        assert result["value"] is None

    def test_invalid_json(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "data.json"
            p.write_text("not json {{")
            result = collect_json_field({"name": "m", "path": str(p), "field": "x"}, Path(d))
        assert result["value"] is None
        assert "json parse error" in result["detail"]


class TestParseDatetimeUtc:
    def test_date_only_returns_end_of_day_utc(self):
        dt = _parse_datetime_utc("2026-04-07")
        assert dt.tzinfo == timezone.utc
        assert dt.hour == 23
        assert dt.minute == 59
        assert dt.second == 59
        assert dt.year == 2026 and dt.month == 4 and dt.day == 7

    def test_iso_with_z_suffix(self):
        dt = _parse_datetime_utc("2026-01-15T12:30:00Z")
        assert dt.tzinfo == timezone.utc
        assert dt.hour == 12
        assert dt.minute == 30

    def test_naive_iso_assumed_utc(self):
        dt = _parse_datetime_utc("2026-03-20T08:00:00")
        assert dt.tzinfo == timezone.utc
        assert dt.hour == 8

    def test_iso_with_offset_converted_to_utc(self):
        # +05:00 means 6am local = 1am UTC
        dt = _parse_datetime_utc("2026-01-01T06:00:00+05:00")
        assert dt.tzinfo == timezone.utc
        assert dt.hour == 1

    def test_date_only_year_boundary(self):
        dt = _parse_datetime_utc("2025-12-31")
        assert dt.year == 2025 and dt.month == 12 and dt.day == 31
