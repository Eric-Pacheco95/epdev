"""Tests for self_diagnose_wrapper.py -- pure helper functions."""
from __future__ import annotations

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

import tools.scripts.self_diagnose_wrapper as sdw


class TestDetectOom:
    def test_winerror_1455(self):
        assert sdw.detect_oom("WinError 1455 blah") is True

    def test_paging_file_message(self):
        assert sdw.detect_oom("The paging file is too small") is True

    def test_memory_error(self):
        assert sdw.detect_oom("MemoryError") is True

    def test_cannot_allocate(self):
        assert sdw.detect_oom("Cannot allocate memory") is True

    def test_errno_12(self):
        assert sdw.detect_oom("[Errno 12] blah") is True

    def test_normal_output_false(self):
        assert sdw.detect_oom("All went fine, 10 tests passed") is False

    def test_empty_string_false(self):
        assert sdw.detect_oom("") is False


class TestDetectFailure:
    def test_nonzero_exit_code(self):
        assert sdw.detect_failure(1, "") is True

    def test_zero_exit_clean_output_false(self):
        assert sdw.detect_failure(0, "Everything went well") is False

    def test_traceback_in_output(self):
        assert sdw.detect_failure(0, "Traceback (most recent call last)\n  line") is True

    def test_error_prefix_in_output(self):
        assert sdw.detect_failure(0, "ERROR: something went wrong") is True

    def test_quality_gate_fail(self):
        assert sdw.detect_failure(0, "QUALITY_GATE: FAIL") is True

    def test_file_not_found_error(self):
        assert sdw.detect_failure(0, "FileNotFoundError: no such file") is True


class TestExtractRunnerName:
    def test_python_script(self):
        assert sdw.extract_runner_name(["python", "tools/scripts/overnight_runner.py"]) == "overnight_runner"

    def test_no_py_file(self):
        assert sdw.extract_runner_name(["echo", "hello"]) == "unknown_runner"

    def test_empty_command(self):
        assert sdw.extract_runner_name([]) == "unknown_runner"

    def test_full_path(self):
        result = sdw.extract_runner_name(["python", r"C:\path\to\morning_feed.py"])
        assert result == "morning_feed"


class TestSanitizeOutput:
    def test_bearer_token_redacted(self):
        out = sdw.sanitize_output("Authorization: Bearer abc123secret")
        assert "abc123secret" not in out
        assert "REDACTED" in out

    def test_normal_line_preserved(self):
        out = sdw.sanitize_output("test passed: 42")
        assert "test passed: 42" in out

    def test_max_lines_truncates(self):
        lines = "\n".join(f"line{i}" for i in range(100))
        result = sdw.sanitize_output(lines, max_lines=10)
        assert "line0" not in result
        assert "line99" in result

    def test_empty_input(self):
        assert sdw.sanitize_output("") == ""

    def test_sk_key_redacted(self):
        out = sdw.sanitize_output("sk-abcdefghijklmnopqrstuvwxyz12345")
        assert "sk-abcdefghijklmnopqrstuvwxyz12345" not in out


class TestExtractField:
    def test_extracts_root_cause(self):
        text = "ROOT_CAUSE: Something broke badly\nSEVERITY: 7"
        assert sdw._extract_field(text, "ROOT_CAUSE", "") == "Something broke badly"

    def test_extracts_severity(self):
        text = "ROOT_CAUSE: x\nSEVERITY: 8\nCATEGORY: import_error"
        assert sdw._extract_field(text, "SEVERITY", "5") == "8"

    def test_missing_field_returns_default(self):
        text = "ROOT_CAUSE: something"
        assert sdw._extract_field(text, "SEVERITY", "5") == "5"

    def test_multiline_first_match(self):
        text = "ROOT_CAUSE: First cause\nROOT_CAUSE: Second cause"
        assert sdw._extract_field(text, "ROOT_CAUSE", "") == "First cause"


class TestExtractFailingTestRefs:
    def test_extracts_test_path(self):
        output = "FAILED tests/test_foo.py::test_bar - AssertionError"
        refs = sdw._extract_failing_test_refs(output)
        assert "tests/test_foo.py::test_bar" in refs

    def test_deduplicates(self):
        output = "tests/test_foo.py\ntests/test_foo.py"
        refs = sdw._extract_failing_test_refs(output)
        assert refs.count("tests/test_foo.py") == 1

    def test_empty_input_returns_empty(self):
        assert sdw._extract_failing_test_refs("") == []

    def test_no_test_refs_returns_empty(self):
        assert sdw._extract_failing_test_refs("All passed successfully") == []

    def test_normalizes_backslash(self):
        output = r"tests\test_foo.py::test_bar"
        refs = sdw._extract_failing_test_refs(output)
        assert "tests/test_foo.py::test_bar" in refs
