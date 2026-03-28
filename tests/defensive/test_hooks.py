#!/usr/bin/env python3
"""Defensive tests: hook scripts import cleanly, handle valid/invalid stdin, exit correctly."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPTS_DIR = REPO_ROOT / "tools" / "scripts"

HOOK_SCRIPTS = [
    "hook_session_start.py",
    "hook_learning_capture.py",
    "hook_notification.py",
    "hook_stop.py",
    "hook_events.py",
]


def _pass(name: str) -> None:
    print(f"PASS: {name}")


def _fail(name: str, detail: str = "") -> None:
    print(f"FAIL: {name}")
    if detail:
        print(f"      {detail}")


def main() -> None:
    ok = True

    # 1. All hook scripts exist
    for script in HOOK_SCRIPTS:
        path = SCRIPTS_DIR / script
        if path.is_file():
            _pass(f"{script} exists")
        else:
            ok = False
            _fail(f"{script} exists", f"not found at {path}")

    # 2. All hook scripts have valid Python syntax (compile check)
    for script in HOOK_SCRIPTS:
        path = SCRIPTS_DIR / script
        if not path.is_file():
            continue
        try:
            compile(path.read_text(encoding="utf-8"), str(path), "exec")
            _pass(f"{script} compiles")
        except SyntaxError as e:
            ok = False
            _fail(f"{script} compiles", str(e))

    # 3. hook_session_start.py runs and exits 0 (no stdin needed)
    result = subprocess.run(
        [sys.executable, str(SCRIPTS_DIR / "hook_session_start.py")],
        cwd=str(REPO_ROOT),
        capture_output=True,
        text=True,
        timeout=15,
    )
    if result.returncode == 0:
        _pass("hook_session_start.py exits 0")
    else:
        ok = False
        _fail("hook_session_start.py exits 0", f"exit={result.returncode} stderr={result.stderr[:200]}")

    # 4. hook_session_start.py output contains expected banner elements
    if "EPDEV Jarvis" in result.stdout and "session start" in result.stdout:
        _pass("hook_session_start.py outputs banner")
    else:
        ok = False
        _fail("hook_session_start.py outputs banner", f"stdout={result.stdout[:200]}")

    # 5. hook_session_start.py output is ASCII-safe (no Unicode crashes on Windows)
    non_ascii = [c for c in result.stdout if ord(c) > 127]
    if not non_ascii:
        _pass("hook_session_start.py ASCII-only output")
    else:
        ok = False
        _fail("hook_session_start.py ASCII-only output", f"found {len(non_ascii)} non-ASCII chars")

    # 6. hook_events.py handles valid PostToolUse JSON without crashing
    valid_event = json.dumps({
        "hook_event_name": "PostToolUse",
        "tool_name": "Bash",
        "session_id": "test-session-123",
        "tool_input": {"command": "echo hello"},
        "tool_response": {"is_error": False, "content": "hello"},
    })
    result = subprocess.run(
        [sys.executable, str(SCRIPTS_DIR / "hook_events.py")],
        input=valid_event,
        cwd=str(REPO_ROOT),
        capture_output=True,
        text=True,
        timeout=10,
    )
    if result.returncode == 0:
        _pass("hook_events.py handles valid PostToolUse")
    else:
        ok = False
        _fail("hook_events.py handles valid PostToolUse", f"exit={result.returncode}")

    # 7. hook_events.py handles empty/invalid stdin without crashing
    result = subprocess.run(
        [sys.executable, str(SCRIPTS_DIR / "hook_events.py")],
        input="not-json",
        cwd=str(REPO_ROOT),
        capture_output=True,
        text=True,
        timeout=10,
    )
    if result.returncode == 0:
        _pass("hook_events.py handles invalid stdin")
    else:
        ok = False
        _fail("hook_events.py handles invalid stdin", f"exit={result.returncode}")

    # 8. hook_events.py writes to JSONL log file
    events_dir = REPO_ROOT / "history" / "events"
    jsonl_files = list(events_dir.glob("*.jsonl")) if events_dir.is_dir() else []
    if jsonl_files:
        _pass("hook_events.py writes JSONL event log")
    else:
        ok = False
        _fail("hook_events.py writes JSONL event log", "no .jsonl files in history/events/")

    # 9. hook_learning_capture.py --help exits 0 (non-interactive check)
    result = subprocess.run(
        [sys.executable, str(SCRIPTS_DIR / "hook_learning_capture.py"), "--help"],
        cwd=str(REPO_ROOT),
        capture_output=True,
        text=True,
        timeout=10,
    )
    if result.returncode == 0:
        _pass("hook_learning_capture.py --help exits 0")
    else:
        ok = False
        _fail("hook_learning_capture.py --help exits 0", f"exit={result.returncode}")

    # 10. hook_stop.py handles valid JSON stdin (mock session end)
    # Note: this will attempt Slack notify which may fail - we only check it doesn't crash
    stop_event = json.dumps({"stop_reason": "end_turn"})
    result = subprocess.run(
        [sys.executable, str(SCRIPTS_DIR / "hook_stop.py")],
        input=stop_event,
        cwd=str(REPO_ROOT),
        capture_output=True,
        text=True,
        timeout=20,
    )
    # Exit 0 means it ran cleanly; non-zero might be Slack auth failure which is OK
    # We just check it doesn't crash with a Python traceback
    if result.returncode == 0:
        _pass("hook_stop.py handles valid stop event")
    elif "Traceback" not in result.stderr:
        _pass("hook_stop.py handles valid stop event (non-zero but no crash)")
    else:
        ok = False
        _fail("hook_stop.py handles valid stop event", f"crash: {result.stderr[:300]}")

    if not ok:
        sys.exit(1)
    print("\nAll hook tests passed.")


if __name__ == "__main__":
    main()
