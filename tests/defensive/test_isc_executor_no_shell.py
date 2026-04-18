"""Tests for isc_executor.py: shell=True removal + MANUAL routing for unsafe commands.

Enforces the orphan-prevention-oom invariant: handle_test must never call
subprocess.run with shell=True. Commands that require shell features route to
MANUAL with a recorded reason.
"""

from __future__ import annotations

import sys
from pathlib import Path
from unittest import mock

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "tools" / "scripts"))

from isc_executor import handle_test, dispatch  # noqa: E402


class TestNoShellTrue:
    """subprocess.run must be invoked with shell=False (default) and argv list."""

    def test_simple_command_uses_list_and_no_shell(self):
        with mock.patch("isc_executor.subprocess.run") as mocked:
            mocked.return_value = mock.Mock(returncode=0, stdout="ok", stderr="")
            handle_test("python --version")
            assert mocked.called
            args, kwargs = mocked.call_args
            # First positional arg is the command -- must be a list, not a string
            assert isinstance(args[0], list), f"expected list argv, got {type(args[0])}"
            assert args[0] == ["python", "--version"]
            # shell must be absent or explicitly False
            assert kwargs.get("shell", False) is False, "shell=True is forbidden"

    def test_quoted_args_preserved(self):
        with mock.patch("isc_executor.subprocess.run") as mocked:
            mocked.return_value = mock.Mock(returncode=0, stdout="", stderr="")
            handle_test('python -c "print(1)"')
            args, _ = mocked.call_args
            assert args[0] == ["python", "-c", "print(1)"]


class TestManualRouting:
    """Commands with shell features route to MANUAL -- never shell=True fallback."""

    @pytest.mark.parametrize("shell_cmd", [
        "pytest && echo ok",
        "grep foo bar.txt || echo miss",
        "ls | head -n 5",
        "cmd1; cmd2",
        "python script.py > out.log",
        "python script.py >> out.log",
        "python script.py 2> err.log",
        "cat < input.txt",
    ])
    def test_shell_operators_route_to_manual(self, shell_cmd):
        evidence, verdict = handle_test(shell_cmd)
        assert verdict == "MANUAL", f"expected MANUAL for {shell_cmd!r}, got {verdict}"
        assert "shell operator" in evidence.lower() or "route to manual" in evidence.lower()

    def test_unshlexable_quotes_route_to_manual(self):
        # Unmatched quote -- shlex raises ValueError
        evidence, verdict = handle_test('python -c "unterminated')
        assert verdict == "MANUAL"
        assert "shlex" in evidence.lower() or "parse" in evidence.lower()

    def test_empty_command_route_to_manual(self):
        evidence, verdict = handle_test("")
        assert verdict == "MANUAL"

    def test_manual_never_invokes_subprocess(self):
        with mock.patch("isc_executor.subprocess.run") as mocked:
            handle_test("pytest && echo ok")
            assert not mocked.called, "MANUAL-routed command must not spawn subprocess"


class TestDispatchPassesThroughVerdict:
    """Dispatcher must propagate MANUAL verdict from handle_test, not coerce to FAIL."""

    def test_test_prefix_propagates_manual(self):
        evidence, verdict = dispatch("Test: ls | grep foo")
        assert verdict == "MANUAL"

    def test_test_prefix_propagates_pass(self):
        with mock.patch("isc_executor.subprocess.run") as mocked:
            mocked.return_value = mock.Mock(returncode=0, stdout="hi", stderr="")
            evidence, verdict = dispatch("Test: echo hi")
            assert verdict == "PASS"

    def test_test_prefix_propagates_fail(self):
        with mock.patch("isc_executor.subprocess.run") as mocked:
            mocked.return_value = mock.Mock(returncode=1, stdout="", stderr="boom")
            evidence, verdict = dispatch("Test: false")
            assert verdict == "FAIL"


class TestShellTrueAbsent:
    """Source-level invariant: the literal shell-enable kwarg must not appear anywhere
    in isc_executor.py (matching the PRD's grep-based acceptance criterion)."""

    def test_no_shell_true_literal_in_source(self):
        src = (REPO_ROOT / "tools" / "scripts" / "isc_executor.py").read_text(encoding="utf-8")
        needle = "shell" + "=" + "True"  # avoid the needle appearing in this test file
        assert needle not in src, f"{needle!r} found in isc_executor.py"
