"""Tests for collectors.core._find_prd_files glob resolution."""

import os
import tempfile
from pathlib import Path
from collectors.core import _find_prd_files


def test_find_prd_files_wildcard():
    with tempfile.TemporaryDirectory() as tmpdir:
        root = Path(tmpdir)
        # Create memory/work/project1/PRD.md and memory/work/project2/PRD.md
        for proj in ["project1", "project2"]:
            d = root / "memory" / "work" / proj
            d.mkdir(parents=True)
            (d / "PRD.md").write_text("- [ ] ISC item")
        # Also a dir with no PRD.md
        (root / "memory" / "work" / "project3").mkdir(parents=True)

        files = _find_prd_files(root, "memory/work/*/PRD.md")
    assert len(files) == 2
    assert all(f.name == "PRD.md" for f in files)


def test_find_prd_files_direct_path():
    with tempfile.TemporaryDirectory() as tmpdir:
        root = Path(tmpdir)
        prd = root / "PRD.md"
        prd.write_text("- [ ] item")

        files = _find_prd_files(root, "PRD.md")
    assert len(files) == 1


def test_find_prd_files_no_match():
    with tempfile.TemporaryDirectory() as tmpdir:
        files = _find_prd_files(Path(tmpdir), "nonexistent/*/PRD.md")
    assert files == []


def test_find_prd_files_direct_path_missing():
    with tempfile.TemporaryDirectory() as tmpdir:
        files = _find_prd_files(Path(tmpdir), "missing.md")
    assert files == []
