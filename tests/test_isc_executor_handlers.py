"""Tests for isc_executor.py -- handle_exist, handle_read, handle_manual, dispatch."""
from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import patch

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from tools.scripts.isc_executor import (
    handle_exist,
    handle_read,
    handle_manual,
    dispatch,
    _resolve_path,
)
import tools.scripts.isc_executor as ie_mod


class TestHandleExist:
    def test_existing_file_passes(self, tmp_path):
        f = tmp_path / "test.md"
        f.write_text("hello", encoding="utf-8")
        with patch.object(ie_mod, "_resolve_path", return_value=f):
            evidence, passed = handle_exist(str(f))
        assert passed is True
        assert "found" in evidence

    def test_missing_file_fails(self, tmp_path):
        missing = tmp_path / "missing.md"
        with patch.object(ie_mod, "_resolve_path", return_value=missing):
            evidence, passed = handle_exist("missing.md")
        assert passed is False
        assert "not found" in evidence

    def test_existing_dir_passes(self, tmp_path):
        d = tmp_path / "subdir"
        d.mkdir()
        with patch.object(ie_mod, "_resolve_path", return_value=d):
            evidence, passed = handle_exist(str(d))
        assert passed is True
        assert "directory" in evidence


class TestHandleRead:
    def test_file_exists_no_contains(self, tmp_path):
        f = tmp_path / "report.md"
        f.write_text("some content", encoding="utf-8")
        with patch.object(ie_mod, "_resolve_path", return_value=f):
            evidence, passed = handle_read("report.md")
        assert passed is True
        assert "exists" in evidence

    def test_missing_file_no_contains(self, tmp_path):
        missing = tmp_path / "nope.md"
        with patch.object(ie_mod, "_resolve_path", return_value=missing):
            evidence, passed = handle_read("nope.md")
        assert passed is False
        assert "not found" in evidence

    def test_contains_match_passes(self, tmp_path):
        f = tmp_path / "output.md"
        f.write_text("PASS: all criteria met", encoding="utf-8")
        with patch.object(ie_mod, "_resolve_path", return_value=f):
            evidence, passed = handle_read(f'output.md contains "PASS:"')
        assert passed is True
        assert "found" in evidence

    def test_contains_no_match_fails(self, tmp_path):
        f = tmp_path / "output.md"
        f.write_text("nothing here", encoding="utf-8")
        with patch.object(ie_mod, "_resolve_path", return_value=f):
            evidence, passed = handle_read(f'output.md contains "PASS:"')
        assert passed is False
        assert "NOT found" in evidence

    def test_contains_missing_file_fails(self, tmp_path):
        missing = tmp_path / "nope.md"
        with patch.object(ie_mod, "_resolve_path", return_value=missing):
            evidence, passed = handle_read(f'nope.md contains "hello"')
        assert passed is False
        assert "not found" in evidence


class TestHandleManual:
    def test_returns_manual_verdict(self):
        _, verdict = handle_manual("Check the output manually", "")
        assert verdict == "MANUAL"

    def test_empty_prefix(self):
        instruction, verdict = handle_manual("Do something", "")
        assert "Do something" in instruction
        assert verdict == "MANUAL"

    def test_prefix_prepended(self):
        instruction, verdict = handle_manual("check deployment", "CLI: ")
        assert "CLI:" in instruction
        assert "check deployment" in instruction

    def test_empty_body(self):
        instruction, verdict = handle_manual("", "Review: ")
        assert verdict == "MANUAL"


class TestDispatch:
    def test_unknown_prefix_returns_manual(self):
        _, verdict = dispatch("Unknown: do something")
        assert verdict == "MANUAL"

    def test_empty_string_returns_manual(self):
        _, verdict = dispatch("")
        assert verdict == "MANUAL"

    def test_review_prefix_returns_manual(self):
        _, verdict = dispatch("Review: verify the output looks correct")
        assert verdict == "MANUAL"

    def test_cli_prefix_returns_manual(self):
        _, verdict = dispatch("CLI: run some command")
        assert verdict == "MANUAL"

    def test_informal_prose_returns_manual(self):
        _, verdict = dispatch("Just verify it works correctly")
        assert verdict == "MANUAL"

    def test_model_annotation_stripped(self):
        _, verdict = dispatch("Review: check output | model: sonnet |")
        assert verdict == "MANUAL"

    def test_compound_method_all_pass(self, tmp_path):
        f1 = tmp_path / "a.md"
        f1.write_text("hello", encoding="utf-8")
        f2 = tmp_path / "b.md"
        f2.write_text("world", encoding="utf-8")
        with patch.object(ie_mod, "_resolve_path", side_effect=[f1, f2]):
            _, verdict = dispatch(f"Exist: {f1} + Exist: {f2}")
        assert verdict == "PASS"

    def test_compound_method_one_fail(self, tmp_path):
        f1 = tmp_path / "a.md"
        f1.write_text("hello", encoding="utf-8")
        missing = tmp_path / "missing.md"
        with patch.object(ie_mod, "_resolve_path", side_effect=[f1, missing]):
            _, verdict = dispatch(f"Exist: {f1} + Exist: {missing}")
        assert verdict == "FAIL"

    def test_exist_dispatch_found(self, tmp_path):
        f = tmp_path / "file.md"
        f.write_text("x", encoding="utf-8")
        with patch.object(ie_mod, "_resolve_path", return_value=f):
            _, verdict = dispatch(f"Exist: {f}")
        assert verdict == "PASS"

    def test_exist_dispatch_missing(self, tmp_path):
        missing = tmp_path / "gone.md"
        with patch.object(ie_mod, "_resolve_path", return_value=missing):
            _, verdict = dispatch(f"Exist: {missing}")
        assert verdict == "FAIL"
