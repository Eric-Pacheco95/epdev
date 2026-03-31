"""Tests for collectors.core derived and checkbox collectors."""

import tempfile
from pathlib import Path
from collectors.core import collect_derived, collect_checkbox_count, collect_prd_checkbox


def test_derived_isc_ratio_basic():
    cfg = {"name": "isc_ratio", "type": "derived"}
    result = collect_derived(cfg, Path("."), current_metrics={"isc_met": 8, "isc_open": 2})
    assert result["value"] == 0.8
    assert result["unit"] == "ratio"


def test_derived_isc_ratio_all_met():
    cfg = {"name": "isc_ratio", "type": "derived"}
    result = collect_derived(cfg, Path("."), current_metrics={"isc_met": 10, "isc_open": 0})
    assert result["value"] == 1.0


def test_derived_isc_ratio_none_met():
    cfg = {"name": "isc_ratio", "type": "derived"}
    result = collect_derived(cfg, Path("."), current_metrics={"isc_met": 0, "isc_open": 5})
    assert result["value"] == 0.0


def test_derived_no_metrics():
    cfg = {"name": "isc_ratio", "type": "derived"}
    result = collect_derived(cfg, Path("."), current_metrics=None)
    assert result["value"] is None


def test_checkbox_count_with_file():
    with tempfile.NamedTemporaryFile(mode="w", suffix=".md", delete=False) as f:
        f.write("- [ ] Task one\n- [x] Task two\n- [ ] Task three\n")
        f.flush()
        cfg = {"name": "open_tasks", "path": f.name, "type": "checkbox_count"}
        result = collect_checkbox_count(cfg, Path("/"))
    assert result["value"] == 2  # only open checkboxes


def test_checkbox_count_missing_file():
    cfg = {"name": "open_tasks", "path": "/nonexistent/file.md", "type": "checkbox_count"}
    result = collect_checkbox_count(cfg, Path("/"))
    assert result["value"] is None
