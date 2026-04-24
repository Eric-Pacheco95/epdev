"""Unit tests for tools/scripts/self_diagnose_wrapper.py pure helpers."""

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from tools.scripts.self_diagnose_wrapper import (
    detect_oom,
    detect_failure,
    extract_runner_name,
    sanitize_output,
    _extract_field,
    _extract_failing_test_refs,
)


class TestDetectOom:
    def test_winerror_1455_detected(self):
        assert detect_oom("fatal error WinError 1455 pagefile exhausted") is True

    def test_paging_file_detected(self):
        assert detect_oom("The paging file is too small for this operation") is True

    def test_clean_output_not_oom(self):
        assert detect_oom("all tests passed") is False

    def test_empty_string_not_oom(self):
        assert detect_oom("") is False

    def test_unrelated_error_not_oom(self):
        assert detect_oom("FileNotFoundError: no such file") is False


class TestDetectFailure:
    def test_nonzero_exit_is_failure(self):
        assert detect_failure(1, "") is True

    def test_zero_clean_output_not_failure(self):
        assert detect_failure(0, "1642 passed in 45s") is False

    def test_zero_with_error_marker_is_failure(self):
        assert detect_failure(0, "Traceback (most recent call last):") is True


class TestExtractRunnerName:
    def test_extracts_py_script(self):
        assert extract_runner_name(["python", "tools/scripts/overnight_runner.py"]) == "overnight_runner"

    def test_extracts_from_nested_path(self):
        assert extract_runner_name(["python", "-m", "tools/scripts/heartbeat.py"]) == "heartbeat"

    def test_no_py_file_returns_unknown(self):
        assert extract_runner_name(["python", "-m", "pytest"]) == "unknown_runner"

    def test_empty_command_returns_unknown(self):
        assert extract_runner_name([]) == "unknown_runner"


class TestSanitizeOutput:
    def test_truncates_to_max_lines(self):
        lines = [f"line {i}" for i in range(100)]
        result = sanitize_output("\n".join(lines), max_lines=10)
        assert len(result.splitlines()) == 10

    def test_takes_last_lines(self):
        lines = [f"line {i}" for i in range(10)]
        result = sanitize_output("\n".join(lines), max_lines=3)
        assert "line 9" in result
        assert "line 0" not in result

    def test_secret_bearer_redacted(self):
        output = "Authorization: Bearer sk-secrettoken123456789012345"
        result = sanitize_output(output)
        assert "Bearer" not in result or "[REDACTED" in result

    def test_clean_output_unchanged(self):
        output = "All tests passed\nExit code: 0"
        result = sanitize_output(output)
        assert "All tests passed" in result


class TestExtractField:
    def test_extracts_root_cause(self):
        text = "ROOT_CAUSE: memory leak in dispatcher\nSEVERITY: 6"
        assert _extract_field(text, "ROOT_CAUSE", "unknown") == "memory leak in dispatcher"

    def test_extracts_severity(self):
        text = "ROOT_CAUSE: bug\nSEVERITY: 8"
        assert _extract_field(text, "SEVERITY", "5") == "8"

    def test_missing_field_returns_default(self):
        assert _extract_field("no fields here", "ROOT_CAUSE", "fallback") == "fallback"

    def test_multiline_picks_first_match(self):
        text = "CATEGORY: network\nCATEGORY: other"
        assert _extract_field(text, "CATEGORY", "") == "network"

    def test_strips_whitespace(self):
        text = "ROOT_CAUSE:   lots of spaces   "
        assert _extract_field(text, "ROOT_CAUSE", "") == "lots of spaces"


class TestExtractFailingTestRefs:
    def test_extracts_test_path(self):
        output = "FAILED tests/test_foo.py::test_bar - AssertionError"
        refs = _extract_failing_test_refs(output)
        assert "tests/test_foo.py::test_bar" in refs

    def test_extracts_plain_test_path(self):
        output = "ERROR collecting tests/test_something.py"
        refs = _extract_failing_test_refs(output)
        assert "tests/test_something.py" in refs

    def test_backslash_normalized(self):
        output = r"FAILED tests\test_foo.py::test_bar"
        refs = _extract_failing_test_refs(output)
        assert all("/" in r for r in refs)

    def test_deduplicates(self):
        output = "FAILED tests/test_foo.py::test_a\nFAILED tests/test_foo.py::test_a"
        refs = _extract_failing_test_refs(output)
        assert refs.count("tests/test_foo.py::test_a") == 1

    def test_empty_input_returns_empty(self):
        assert _extract_failing_test_refs("") == []

    def test_no_test_refs_returns_empty(self):
        assert _extract_failing_test_refs("all tests passed in 3.4s") == []
