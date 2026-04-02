"""Tests for collectors.core miscellaneous functions."""

import os
import tempfile
from pathlib import Path
from tools.scripts.collectors.core import (
    _dir_size_mb, reset_query_cache, _query_events_cache,
    COLLECTOR_TYPES, collect_hook_output_size,
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
    reset_query_cache()
    assert mod._query_events_cache is None


def test_collector_types_registry():
    """Verify all expected collector types are registered."""
    expected = {
        "file_count", "file_count_velocity", "checkbox_count",
        "checkbox_delta", "prd_checkbox", "derived", "query_events",
        "file_recency", "dir_count", "disk_usage", "hook_output_size",
        "scheduled_tasks", "auth_health", "signal_volume",
        "manifest_signal_count", "manifest_signal_velocity",
        "autonomous_signal_rate", "manifest_autonomous_signal_rate",
        "producer_health",
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
