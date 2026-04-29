"""Tests for collectors.core run_collector dispatcher and dir/file collectors."""

import tempfile
import os
from pathlib import Path
from collectors.core import run_collector, collect_dir_count, collect_file_count, collect_file_count_velocity


def test_run_collector_unknown_type():
    cfg = {"name": "test", "type": "nonexistent_type"}
    result = run_collector(cfg, Path("."))
    assert result["value"] is None
    assert "unknown collector type" in result["detail"]


def test_run_collector_derived_dispatch():
    cfg = {"name": "isc_ratio", "type": "derived"}
    result = run_collector(cfg, Path("."), current_metrics={"isc_met": 5, "isc_open": 5})
    assert result["value"] == 0.5


def test_dir_count():
    with tempfile.TemporaryDirectory() as tmpdir:
        # Create 3 subdirectories
        for name in ["a", "b", "c"]:
            os.makedirs(os.path.join(tmpdir, name))
        # Create a file (should not be counted)
        with open(os.path.join(tmpdir, "file.txt"), "w") as f:
            f.write("not a dir")
        cfg = {"name": "subdir_count", "path": tmpdir, "type": "dir_count"}
        result = collect_dir_count(cfg, Path("/"))
    assert result["value"] == 3


def test_file_count():
    with tempfile.TemporaryDirectory() as tmpdir:
        for name in ["a.md", "b.md", "c.txt"]:
            with open(os.path.join(tmpdir, name), "w") as f:
                f.write("content")
        cfg = {"name": "md_files", "path": tmpdir, "ext": ".md", "type": "file_count"}
        result = collect_file_count(cfg, Path("/"))
    assert result["value"] == 2


def test_file_count_missing_dir():
    cfg = {"name": "test", "path": "/nonexistent/dir", "type": "file_count"}
    result = collect_file_count(cfg, Path("/"))
    assert result["value"] is None


def test_dir_count_empty_dir():
    with tempfile.TemporaryDirectory() as tmpdir:
        cfg = {"name": "subdir_count", "path": tmpdir, "type": "dir_count"}
        result = collect_dir_count(cfg, Path("/"))
    assert result["value"] == 0


def test_dir_count_missing_dir():
    cfg = {"name": "subdir_count", "path": "/nonexistent/path", "type": "dir_count"}
    result = collect_dir_count(cfg, Path("/"))
    assert result["value"] is None


def test_run_collector_file_count_dispatch():
    with tempfile.TemporaryDirectory() as tmpdir:
        Path(tmpdir, "x.md").write_text("a")
        cfg = {"name": "md_count", "path": tmpdir, "ext": ".md", "type": "file_count"}
        result = run_collector(cfg, Path("/"))
    assert result["value"] == 1


def test_file_count_velocity_recent_files():
    with tempfile.TemporaryDirectory() as tmpdir:
        for name in ["a.md", "b.md"]:
            Path(tmpdir, name).write_text("x")
        cfg = {"name": "velocity", "path": tmpdir, "ext": ".md",
               "window_days": 7, "type": "file_count_velocity"}
        result = collect_file_count_velocity(cfg, Path("/"))
    assert result["value"] is not None
    assert result["unit"] == "per_day"


def test_file_count_velocity_missing_dir():
    cfg = {"name": "velocity", "path": "/nonexistent/dir", "ext": ".md",
           "window_days": 7, "type": "file_count_velocity"}
    result = collect_file_count_velocity(cfg, Path("/"))
    assert result["value"] is None


def test_file_count_velocity_empty_dir():
    with tempfile.TemporaryDirectory() as tmpdir:
        cfg = {"name": "velocity", "path": tmpdir, "ext": ".md",
               "window_days": 7, "type": "file_count_velocity"}
        result = collect_file_count_velocity(cfg, Path("/"))
    assert result["value"] == 0.0
