"""Integration tests for tools/scripts/lib/windows_job.py -- cascade-kill proof.

These tests PROVE that the Job Object primitive kills grandchildren on timeout.
Without this guarantee, Phase 3 of orphan-prevention-oom is non-load-bearing --
the entire architectural fix depends on descendant termination cascading.

Tests spawn a root process that launches a long-running grandchild, force a
timeout, and assert via psutil that the grandchild PID is gone within 5 seconds.
"""

from __future__ import annotations

import subprocess
import sys
import time
from pathlib import Path

import pytest

if sys.platform != "win32":
    pytest.skip("Windows-only tests", allow_module_level=True)

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "tools" / "scripts"))

from lib.windows_job import run_with_job_object  # noqa: E402

try:
    import psutil
except ImportError:
    pytest.skip("psutil not available", allow_module_level=True)


def _pid_alive(pid: int) -> bool:
    try:
        proc = psutil.Process(pid)
        return proc.is_running() and proc.status() != psutil.STATUS_ZOMBIE
    except (psutil.NoSuchProcess, psutil.AccessDenied):
        return False


def _wait_pid_gone(pid: int, deadline_s: float) -> bool:
    """Poll until pid is gone or deadline elapses. Returns True if gone."""
    end = time.monotonic() + deadline_s
    while time.monotonic() < end:
        if not _pid_alive(pid):
            return True
        time.sleep(0.05)
    return False


class TestCascadeKillOnTimeout:
    """Primary cascade-kill integration test (ISC #9)."""

    def test_grandchild_dies_on_timeout(self, tmp_path):
        """Root spawns python grandchild that sleeps 300s; on 3s timeout, grandchild PID gone <5s.

        Uses a PID file (not stdout) to capture the grandchild PID reliably --
        stdout buffering makes `print()` capture racy when the parent is killed
        mid-execution by job termination.
        """
        pid_file = tmp_path / "gc.pid"
        pid_file_str = str(pid_file).replace("\\", "\\\\")

        # Root: spawn grandchild, write its PID to file, then sleep forever.
        # The grandchild sleeps 300s (long enough to outlive the timeout).
        root_script = (
            "import subprocess, sys, time; "
            f"p = subprocess.Popen([sys.executable, '-c', 'import time; time.sleep(300)']); "
            f"open(r'{pid_file_str}', 'w').write(str(p.pid)); "
            "time.sleep(300)"
        )
        cmd = [sys.executable, "-c", root_script]

        start = time.monotonic()
        with pytest.raises(subprocess.TimeoutExpired):
            # 3s timeout: plenty of time for PID file to be written; short
            # enough that grandchild is still sleeping when job is terminated.
            run_with_job_object(cmd, timeout=3)
        elapsed = time.monotonic() - start

        assert elapsed < 15, f"timeout path took {elapsed}s (expected <15s)"

        # Grandchild PID must have been recorded (proves root got far enough
        # to spawn a grandchild before the job was terminated).
        assert pid_file.exists(), (
            "grandchild PID file never written -- test setup failed; "
            "root process may have been killed before spawning grandchild"
        )
        try:
            gc_pid = int(pid_file.read_text().strip())
        except ValueError:
            pytest.fail(f"could not parse PID file: {pid_file.read_text()!r}")

        # The grandchild must be gone within 5 seconds of timeout.
        assert _wait_pid_gone(gc_pid, deadline_s=5.0), (
            f"grandchild pid {gc_pid} still alive 5s after timeout -- "
            f"cascade-kill FAILED -- Job Object KILL_ON_JOB_CLOSE broken"
        )


class TestHappyPathReturnsCompletedProcess:
    """Non-timeout path returns a CompletedProcess that matches subprocess.run semantics."""

    def test_returns_completed_process_on_success(self):
        result = run_with_job_object(
            [sys.executable, "-c", "print('hi')"],
            timeout=10,
        )
        assert isinstance(result, subprocess.CompletedProcess)
        assert result.returncode == 0
        assert "hi" in (result.stdout or "")

    def test_nonzero_exit_preserved(self):
        result = run_with_job_object(
            [sys.executable, "-c", "import sys; sys.exit(7)"],
            timeout=10,
        )
        assert result.returncode == 7

    def test_stdin_input_delivered(self):
        result = run_with_job_object(
            [sys.executable, "-c", "import sys; print(sys.stdin.read().upper())"],
            timeout=10,
            input="hello",
        )
        assert "HELLO" in (result.stdout or "")


class TestTypeSafety:
    """Contract: argv list only. String commands are rejected."""

    def test_string_command_rejected(self):
        with pytest.raises(TypeError, match="argv list"):
            run_with_job_object("python --version", timeout=5)
