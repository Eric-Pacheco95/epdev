"""Tests for tools.scripts.lib.isc_templates and verify helper scripts."""
from __future__ import annotations

import os

# Avoid writing data/isc_template_usage.jsonl during unit tests
os.environ["JARVIS_ISC_TEMPLATE_LOG"] = "0"

import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]

from tools.scripts.lib.isc_common import classify_verify_method, sanitize_isc_command
from tools.scripts.lib.isc_templates import (
    GAP_ADD_TESTS,
    GAP_FIX_LINT,
    GAP_REMOVE_DEAD_CODE,
    GAP_UPDATE_DOCS,
    UnsafePathError,
    isc_add_tests,
    isc_fix_lint,
    isc_from_gap,
    isc_remove_dead_code,
    isc_update_docs,
    normalize_repo_rel_path,
)


def _assert_executable_isc(line: str) -> None:
    assert "| Verify:" in line
    assert classify_verify_method(line) in ("executable", "prd_verb")
    if classify_verify_method(line) == "executable":
        assert sanitize_isc_command(line) is not None


def test_normalize_rejects_dotdot():
    with pytest.raises(UnsafePathError):
        normalize_repo_rel_path("foo/../bar.py")


def test_isc_add_tests_classifies():
    for line in isc_add_tests("tests/test_foo.py", impl_file="tools/scripts/lib/isc_common.py"):
        _assert_executable_isc(line)


def test_isc_fix_lint_self_file():
    tf = "tools/scripts/lib/isc_templates.py"
    for line in isc_fix_lint(tf):
        _assert_executable_isc(line)


def test_isc_remove_dead_code():
    for line in isc_remove_dead_code("path/does_not_exist_zz_12345.py"):
        _assert_executable_isc(line)


def test_isc_update_docs_anchor_invalid():
    with pytest.raises(UnsafePathError):
        isc_update_docs("README.md", "two words")


def test_isc_from_gap_dispatch():
    lst = isc_from_gap(
        GAP_UPDATE_DOCS,
        doc_file="CLAUDE.md",
        anchor_substring="Jarvis",
    )
    assert len(lst) == 2
    for line in lst:
        _assert_executable_isc(line)


def test_isc_from_gap_unknown_kind():
    with pytest.raises(ValueError):
        isc_from_gap("unknown_kind", test_file="x.py")


def test_verify_py_compile_runs_on_self():
    proc = subprocess.run(
        [sys.executable, str(REPO_ROOT / "tools/scripts/verify_py_compile.py"),
         "tools/scripts/verify_py_compile.py"],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
    )
    assert proc.returncode == 0, proc.stderr


def test_verify_repo_path_absent_missing_ok():
    proc = subprocess.run(
        [sys.executable, str(REPO_ROOT / "tools/scripts/verify_repo_path_absent.py"),
         "path/absent_file_never_created_zz99.txt"],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
    )
    assert proc.returncode == 0, proc.stderr


def test_gap_constants_unique():
    kinds = {GAP_ADD_TESTS, GAP_FIX_LINT, GAP_REMOVE_DEAD_CODE, GAP_UPDATE_DOCS}
    assert len(kinds) == 4
