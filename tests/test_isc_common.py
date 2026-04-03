"""Tests for lib/isc_common -- ISC command sanitization and classification."""

from tools.scripts.lib.isc_common import (
    classify_verify_method,
    sanitize_isc_command,
    _extract_cmd,
    _first_word,
    MANUAL_REQUIRED,
)


# ── _extract_cmd ─────────────────────────────────────────────────────

def test_extract_cmd_full_isc():
    result = _extract_cmd("File exists | Verify: test -f foo.py")
    assert result == "test -f foo.py"


def test_extract_cmd_bare():
    result = _extract_cmd("test -f foo.py")
    assert result == "test -f foo.py"


def test_extract_cmd_empty():
    assert _extract_cmd("") is None
    assert _extract_cmd("  ") is None


def test_extract_cmd_verify_empty():
    assert _extract_cmd("Something | Verify:") is None


# ── _first_word ──────────────────────────────────────────────────────

def test_first_word_simple():
    assert _first_word("test -f foo") == "test"


def test_first_word_with_path():
    assert _first_word("/usr/bin/grep pattern") == "grep"


def test_first_word_empty():
    assert _first_word("") == ""


# ── classify_verify_method ───────────────────────────────────────────

def test_classify_executable():
    assert classify_verify_method("test -f foo.py") == "executable"
    assert classify_verify_method("grep pattern file") == "executable"
    assert classify_verify_method("ls tools/scripts/") == "executable"


def test_classify_python_script():
    assert classify_verify_method("python tools/scripts/foo.py") == "executable"


def test_classify_python_c_blocked():
    assert classify_verify_method("python -c 'import os'") == "blocked"
    assert classify_verify_method("python3 -c 'evil'") == "blocked"


def test_classify_python_unknown_blocked():
    assert classify_verify_method("python /tmp/evil.py") == "blocked"


def test_classify_manual_review():
    assert classify_verify_method("Review code for correctness") == MANUAL_REQUIRED


def test_classify_manual_confirm():
    assert classify_verify_method("Confirm with Eric") == MANUAL_REQUIRED


def test_classify_echo():
    assert classify_verify_method("echo ok") == MANUAL_REQUIRED


def test_classify_unknown():
    assert classify_verify_method("some freeform description") == MANUAL_REQUIRED


def test_classify_full_isc():
    result = classify_verify_method("File exists [E] | Verify: test -f foo.py")
    assert result == "executable"


# ── sanitize_isc_command ─────────────────────────────────────────────

def test_sanitize_allowed():
    result = sanitize_isc_command("test -f tools/scripts/foo.py")
    assert result == "test -f tools/scripts/foo.py"


def test_sanitize_pipe():
    result = sanitize_isc_command("grep pattern file.py | wc -l")
    assert result is not None


def test_sanitize_shell_metachar_semicolon():
    assert sanitize_isc_command("test -f foo; rm -rf /") is None


def test_sanitize_shell_metachar_and():
    assert sanitize_isc_command("test -f foo && rm -rf /") is None


def test_sanitize_shell_metachar_subshell():
    assert sanitize_isc_command("test $(whoami)") is None


def test_sanitize_shell_metachar_backtick():
    assert sanitize_isc_command("test `whoami`") is None


def test_sanitize_secret_path_env():
    assert sanitize_isc_command("cat .env") is None


def test_sanitize_secret_path_pem():
    assert sanitize_isc_command("cat server.pem") is None


def test_sanitize_secret_path_ssh():
    assert sanitize_isc_command("cat ~/.ssh/id_rsa") is None


def test_sanitize_disallowed_command():
    assert sanitize_isc_command("rm -rf /tmp/test") is None


def test_sanitize_python_script_allowed():
    result = sanitize_isc_command("python tools/scripts/foo.py --check")
    assert result is not None


def test_sanitize_python_bare_blocked():
    assert sanitize_isc_command("python /tmp/script.py") is None


def test_sanitize_full_isc_string():
    result = sanitize_isc_command("Criterion | Verify: test -f foo.py")
    assert result == "test -f foo.py"
