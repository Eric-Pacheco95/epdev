"""Unit tests for tools/scripts/isc_executor.py pure helpers."""

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from tools.scripts.isc_executor import (
    scrub_secrets,
    _strip_quoted,
    determine_exit_code,
)


class TestScrubSecrets:
    def test_clean_text_unchanged(self):
        text = "All tests passed successfully"
        assert scrub_secrets(text) == text

    def test_sk_key_redacted(self):
        text = "sk-anthropicABCDEFGHIJKLMNOPQRSTUVWXYZ is the api key"
        result = scrub_secrets(text)
        assert "sk-anthropicABCDEFGHIJKLMNOPQRSTUVWXYZ" not in result
        assert "[REDACTED]" in result

    def test_returns_string(self):
        assert isinstance(scrub_secrets("plain text"), str)

    def test_empty_string(self):
        assert scrub_secrets("") == ""


class TestStripQuoted:
    def test_removes_double_quoted_content(self):
        result = _strip_quoted('grep "secret=abc" file.py')
        assert "secret=abc" not in result

    def test_removes_single_quoted_content(self):
        result = _strip_quoted("grep 'hidden' file.py")
        assert "hidden" not in result

    def test_preserves_unquoted_content(self):
        result = _strip_quoted("grep pattern file.py")
        assert "grep" in result
        assert "pattern" in result
        assert "file.py" in result

    def test_empty_string(self):
        assert _strip_quoted("") == ""

    def test_quoted_content_removed_unquoted_preserved(self):
        result = _strip_quoted('cmd "hidden_secret" keepme')
        assert "hidden_secret" not in result
        assert "keepme" in result


class TestDetermineExitCode:
    def test_all_pass_returns_zero(self):
        output = {"summary": {"fail": 0, "error": 0, "manual": 0}, "criteria": [{}]}
        assert determine_exit_code(output) == 0

    def test_fail_count_returns_one(self):
        output = {"summary": {"fail": 1, "error": 0, "manual": 0}, "criteria": [{}]}
        assert determine_exit_code(output) == 1

    def test_error_count_returns_two(self):
        output = {"summary": {"fail": 0, "error": 1, "manual": 0}, "criteria": [{}]}
        assert determine_exit_code(output) == 2

    def test_manual_only_returns_three(self):
        output = {"summary": {"fail": 0, "error": 0, "manual": 2}, "criteria": [{}]}
        assert determine_exit_code(output) == 3

    def test_fail_takes_priority_over_manual(self):
        output = {"summary": {"fail": 1, "error": 0, "manual": 2}, "criteria": [{}]}
        assert determine_exit_code(output) == 1

    def test_fundamental_error_no_criteria(self):
        output = {"errors": ["crash"], "criteria": []}
        assert determine_exit_code(output) == 2

    def test_errors_with_criteria_does_not_short_circuit(self):
        # If criteria exist, we go to normal logic even with errors key populated
        output = {"errors": ["some error"], "criteria": [{}], "summary": {"fail": 0, "error": 0, "manual": 0}}
        assert determine_exit_code(output) == 0

    def test_missing_summary_treated_as_zeros(self):
        output = {"criteria": [{}]}
        assert determine_exit_code(output) == 0
