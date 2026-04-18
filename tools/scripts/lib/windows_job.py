"""Windows Job Object wrapper for subprocess spawning.

Provides `run_with_job_object(cmd, timeout, ...)` -- a drop-in replacement for
`subprocess.run` that guarantees all descendant processes (grandchildren,
great-grandchildren, etc.) are killed when the root process exits or times out.

Rationale (2026-04-18 orphan-prevention-oom): Windows does not cascade
`TerminateProcess` to grandchildren. When `claude.exe` (the root process) times
out and is killed by `subprocess.run(timeout=...)`, its python.exe hook
grandchildren survive and accumulate as orphans. The 9,488-orphan OOM incident
traced to this exact gap at three independent call sites.

Design:
- Create an anonymous Job Object with `JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE`.
  When the last handle to the job is closed, every process still in the job
  (including descendants launched after assignment) is terminated.
- On timeout, call `TerminateJobObject` explicitly (nuclear option -- cascades
  to all descendants in one syscall).
- Hold the job handle until the root process finishes communicate(), then close
  it in `finally`. This is the safety net: if the root exited cleanly but
  detached a grandchild, CloseHandle triggers KILL_ON_JOB_CLOSE and the
  grandchild dies.

This module is Windows-only -- import fails on other platforms.
"""

from __future__ import annotations

import subprocess
import sys
from typing import Any

import psutil
import pywintypes
import win32api
import win32job

if sys.platform != "win32":
    raise ImportError("windows_job is Windows-only")

CREATE_SUSPENDED = 0x00000004


def _create_kill_on_close_job() -> Any:
    """Create an anonymous Job Object with KILL_ON_JOB_CLOSE set. Returns the handle."""
    job = win32job.CreateJobObject(None, "")
    info = win32job.QueryInformationJobObject(
        job, win32job.JobObjectExtendedLimitInformation
    )
    info["BasicLimitInformation"]["LimitFlags"] |= (
        win32job.JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE
    )
    win32job.SetInformationJobObject(
        job, win32job.JobObjectExtendedLimitInformation, info
    )
    return job


def run_with_job_object(
    cmd: list[str],
    timeout: float | None,
    *,
    input: str | bytes | None = None,
    capture_output: bool = True,
    text: bool = True,
    encoding: str | None = "utf-8",
    errors: str | None = None,
    cwd: str | None = None,
    env: dict | None = None,
) -> subprocess.CompletedProcess:
    """Run cmd under a Windows Job Object with KILL_ON_JOB_CLOSE.

    On timeout, terminates the job (cascading to every descendant process) and
    re-raises `subprocess.TimeoutExpired` exactly like `subprocess.run`.

    Args:
        cmd: Argv list (never a string -- shell=True is forbidden here too).
        timeout: Seconds to wait before killing the job and its descendants.
        input: Optional stdin data.
        capture_output: If True, capture stdout/stderr; if False, inherit.
        text: Text mode for I/O.
        encoding: Encoding for text-mode I/O.
        cwd: Working directory.
        env: Environment overrides.

    Returns:
        subprocess.CompletedProcess with args, returncode, stdout, stderr.

    Raises:
        subprocess.TimeoutExpired: On timeout (job is already terminated).
        FileNotFoundError: If cmd[0] cannot be found.
    """
    if isinstance(cmd, str):
        raise TypeError("run_with_job_object requires argv list, not string")

    job = _create_kill_on_close_job()
    proc: subprocess.Popen | None = None
    try:
        stdin_kind = subprocess.PIPE if input is not None else None
        out_kind = subprocess.PIPE if capture_output else None

        # CREATE_SUSPENDED: child is born suspended so no grandchildren can spawn
        # before we assign it to the job. This closes the race where a fast-forking
        # child births orphans in the microseconds between Popen returning and
        # AssignProcessToJobObject firing.
        proc = subprocess.Popen(
            cmd,
            stdin=stdin_kind,
            stdout=out_kind,
            stderr=out_kind,
            text=text,
            encoding=encoding,
            errors=errors,
            cwd=cwd,
            env=env,
            creationflags=CREATE_SUSPENDED,
        )

        # Assign to job while suspended. Windows 8+ supports nested jobs, so even
        # if Python's subprocess placed the child in an implicit job already,
        # ours nests on top. Every process spawned after resume is a member.
        try:
            win32job.AssignProcessToJobObject(job, int(proc._handle))
        except pywintypes.error as exc:
            try:
                psutil.Process(proc.pid).resume()
            except Exception:
                pass
            try:
                proc.kill()
            except Exception:
                pass
            proc.wait()
            raise RuntimeError(
                f"AssignProcessToJobObject failed for pid {proc.pid}: {exc}"
            ) from exc

        # Resume AFTER assignment -- NtResumeProcess wakes all threads in proc.
        try:
            psutil.Process(proc.pid).resume()
        except Exception as exc:
            try:
                proc.kill()
            except Exception:
                pass
            proc.wait()
            raise RuntimeError(
                f"Resume failed for pid {proc.pid}: {exc}"
            ) from exc

        try:
            stdout, stderr = proc.communicate(input=input, timeout=timeout)
            return subprocess.CompletedProcess(
                cmd, proc.returncode, stdout, stderr
            )
        except subprocess.TimeoutExpired:
            # Nuclear: terminate the entire job tree in one syscall.
            try:
                win32job.TerminateJobObject(job, 1)
            except pywintypes.error:
                pass
            # Drain residual output (TerminateJobObject is async; give it a beat).
            try:
                stdout, stderr = proc.communicate(timeout=5)
            except Exception:
                stdout, stderr = ("", "") if text else (b"", b"")
            raise subprocess.TimeoutExpired(
                cmd, timeout, output=stdout, stderr=stderr
            )
    finally:
        # Closing the last handle triggers KILL_ON_JOB_CLOSE, catching any
        # grandchild that detached from the root after it exited normally.
        try:
            win32api.CloseHandle(job)
        except Exception:
            pass
