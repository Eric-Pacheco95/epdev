"""Tests for collectors.core run_collector dispatcher and dir/file collectors."""

import tempfile
import os
from pathlib import Path
from collectors.core import run_collector, collect_dir_count, collect_file_count


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
