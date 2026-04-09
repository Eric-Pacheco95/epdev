"""Tests for self_diagnose_wrapper.py pure helper functions."""

from tools.scripts.self_diagnose_wrapper import (
    detect_failure,
    detect_oom,
    extract_runner_name,
    sanitize_output,
)


# ---------------------------------------------------------------------------
# detect_oom
# ---------------------------------------------------------------------------

def test_detect_oom_clean_output():
    assert detect_oom("All tests passed.") is False


def test_detect_oom_winerror_1455():
    assert detect_oom("WinError 1455: The paging file is too small") is True


def test_detect_oom_out_of_memory():
    assert detect_oom("MemoryError: out of memory") is True


def test_detect_oom_empty():
    assert detect_oom("") is False


# ---------------------------------------------------------------------------
# detect_failure
# ---------------------------------------------------------------------------

def test_detect_failure_nonzero_exit():
    assert detect_failure(1, "") is True


def test_detect_failure_zero_exit_clean():
    assert detect_failure(0, "All good.") is False


def test_detect_failure_zero_exit_with_error_pattern():
    # Many error patterns in the output signal failure even at exit 0
    result = detect_failure(0, "Traceback (most recent call last):\nValueError: bad input")
    assert result is True


# ---------------------------------------------------------------------------
# extract_runner_name
# ---------------------------------------------------------------------------

def test_extract_runner_name_py_script():
    cmd = ["python", "tools/scripts/overnight_runner.py", "--dry-run"]
    assert extract_runner_name(cmd) == "overnight_runner"


def test_extract_runner_name_no_py():
    cmd = ["git", "status"]
    assert extract_runner_name(cmd) == "unknown_runner"


def test_extract_runner_name_empty():
    assert extract_runner_name([]) == "unknown_runner"


# ---------------------------------------------------------------------------
# sanitize_output
# ---------------------------------------------------------------------------

def test_sanitize_output_no_secrets():
    output = "line1\nline2\nline3"
    result = sanitize_output(output)
    assert "line1" in result
    assert "line2" in result


def test_sanitize_output_redacts_bearer():
    output = "Authorization: Bearer abc123secret\nSome normal line."
    result = sanitize_output(output)
    assert "abc123secret" not in result
    assert "[REDACTED" in result


def test_sanitize_output_redacts_sk_key():
    output = "Using key: sk-abcdefghij1234567890"
    result = sanitize_output(output)
    assert "sk-abcdefghij" not in result
    assert "[REDACTED" in result


def test_sanitize_output_truncates_to_max_lines():
    output = "\n".join(f"line{i}" for i in range(200))
    result = sanitize_output(output, max_lines=10)
    assert result.count("\n") == 9  # 10 lines = 9 newlines
    assert "line199" in result  # last lines kept
