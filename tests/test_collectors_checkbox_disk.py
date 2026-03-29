"""Tests for checkbox_delta and disk_usage collectors."""

import tempfile
import os
from pathlib import Path
from collectors.core import collect_checkbox_delta, collect_disk_usage


def test_checkbox_delta_no_previous():
    with tempfile.NamedTemporaryFile(mode="w", suffix=".md", delete=False) as f:
        f.write("- [ ] Task\n")
        f.flush()
        cfg = {"name": "delta", "path": f.name, "type": "checkbox_delta"}
        result = collect_checkbox_delta(cfg, Path("/"), prev=None)
    assert result["value"] is None
    assert "no previous" in result["detail"]


def test_checkbox_delta_tasks_completed():
    with tempfile.NamedTemporaryFile(mode="w", suffix=".md", delete=False) as f:
        f.write("- [ ] Task one\n- [x] Task two\n")  # 1 open now
        f.flush()
        cfg = {"name": "delta", "path": f.name, "type": "checkbox_delta"}
        prev = {"open_task_count": 3}  # was 3 open before
        result = collect_checkbox_delta(cfg, Path("/"), prev=prev)
    assert result["value"] == 2  # 3 - 1 = 2 completed


def test_checkbox_delta_no_change():
    with tempfile.NamedTemporaryFile(mode="w", suffix=".md", delete=False) as f:
        f.write("- [ ] Task\n")
        f.flush()
        cfg = {"name": "delta", "path": f.name, "type": "checkbox_delta"}
        prev = {"open_task_count": 1}
        result = collect_checkbox_delta(cfg, Path("/"), prev=prev)
    assert result["value"] == 0


def test_disk_usage_file():
    with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
        f.write("x" * 1024)  # 1KB
        f.flush()
        cfg = {"name": "size", "path": f.name, "type": "disk_usage"}
        result = collect_disk_usage(cfg, Path("/"))
    assert result["value"] is not None
    assert result["unit"] == "MB"


def test_disk_usage_directory():
    with tempfile.TemporaryDirectory() as tmpdir:
        for i in range(3):
            with open(os.path.join(tmpdir, f"file{i}.txt"), "w") as f:
                f.write("data" * 100)
        cfg = {"name": "dir_size", "path": tmpdir, "type": "disk_usage"}
        result = collect_disk_usage(cfg, Path("/"))
    assert result["value"] >= 0
    assert result["unit"] == "MB"


def test_disk_usage_missing_path():
    cfg = {"name": "size", "path": "/nonexistent/path", "type": "disk_usage"}
    result = collect_disk_usage(cfg, Path("/"))
    assert result["value"] is None
