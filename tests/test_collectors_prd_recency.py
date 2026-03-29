"""Tests for prd_checkbox and file_recency collectors."""

import tempfile
import os
import time
from pathlib import Path
from collectors.core import collect_prd_checkbox, collect_file_recency


def test_prd_checkbox_open_count():
    with tempfile.TemporaryDirectory() as tmpdir:
        prd = os.path.join(tmpdir, "PRD.md")
        with open(prd, "w") as f:
            f.write("# PRD\n- [ ] ISC 1\n- [x] ISC 2\n- [ ] ISC 3\n")
        # _find_prd_files expects root/glob structure; use direct file path
        cfg = {"name": "isc_open", "type": "prd_checkbox",
               "checkbox_state": "open", "prd_glob": "PRD.md"}
        result = collect_prd_checkbox(cfg, Path(tmpdir))
    assert result["value"] == 2


def test_prd_checkbox_met_count():
    with tempfile.TemporaryDirectory() as tmpdir:
        prd = os.path.join(tmpdir, "PRD.md")
        with open(prd, "w") as f:
            f.write("- [x] Done 1\n- [X] Done 2\n- [ ] Open\n")
        cfg = {"name": "isc_met", "type": "prd_checkbox",
               "checkbox_state": "met", "prd_glob": "PRD.md"}
        result = collect_prd_checkbox(cfg, Path(tmpdir))
    assert result["value"] == 2


def test_prd_checkbox_skips_code_blocks():
    with tempfile.TemporaryDirectory() as tmpdir:
        prd = os.path.join(tmpdir, "PRD.md")
        with open(prd, "w") as f:
            f.write("- [ ] Real ISC\n```\n- [ ] In code block\n```\n- [ ] Another real\n")
        cfg = {"name": "isc_open", "type": "prd_checkbox",
               "checkbox_state": "open", "prd_glob": "PRD.md"}
        result = collect_prd_checkbox(cfg, Path(tmpdir))
    assert result["value"] == 2  # code block checkbox excluded


def test_prd_checkbox_no_files():
    with tempfile.TemporaryDirectory() as tmpdir:
        cfg = {"name": "isc_open", "type": "prd_checkbox",
               "prd_glob": "nonexistent/PRD.md"}
        result = collect_prd_checkbox(cfg, Path(tmpdir))
    assert result["value"] is None


def test_file_recency_single_file():
    with tempfile.NamedTemporaryFile(mode="w", suffix=".md", delete=False) as f:
        f.write("recent file")
        f.flush()
        cfg = {"name": "recency", "path": f.name, "type": "file_recency"}
        result = collect_file_recency(cfg, Path("/"))
    assert result["value"] == 0  # modified today = 0 days
    assert result["unit"] == "days_since"


def test_file_recency_missing_path():
    cfg = {"name": "recency", "path": "/nonexistent/file.md", "type": "file_recency"}
    result = collect_file_recency(cfg, Path("/"))
    assert result["value"] is None
