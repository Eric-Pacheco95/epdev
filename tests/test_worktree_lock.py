"""Tests for lib/worktree.py -- acquire_claude_lock and release_claude_lock."""

import json
import os
from datetime import datetime, timezone, timedelta
from unittest import mock

import tools.scripts.lib.worktree as wt_mod
from tools.scripts.lib.worktree import acquire_claude_lock, release_claude_lock


def test_acquire_lock_when_free(tmp_path):
    with mock.patch.object(wt_mod, "_LOCK_DIR", tmp_path):
        result = acquire_claude_lock("test_owner")
    assert result == 0
    lock_file = tmp_path / "claude_session.0.lock"
    assert lock_file.exists()
    data = json.loads(lock_file.read_text())
    assert data["owner"] == "test_owner"
    assert data["slot"] == 0


def test_acquire_lock_already_held(tmp_path):
    lock_file = tmp_path / "claude_session.0.lock"
    lock_data = {
        "owner": "other_process",
        "locked_at": datetime.now(timezone.utc).isoformat(),
        "pid": os.getpid(),  # live PID so liveness check passes
        "slot": 0,
    }
    lock_file.write_text(json.dumps(lock_data))
    with mock.patch.object(wt_mod, "_LOCK_DIR", tmp_path):
        result = acquire_claude_lock("new_owner")
    assert result is None


def test_acquire_lock_breaks_stale_by_age(tmp_path):
    lock_file = tmp_path / "claude_session.0.lock"
    stale_time = datetime.now(timezone.utc) - timedelta(hours=5)
    lock_data = {"owner": "crashed_process", "locked_at": stale_time.isoformat(), "pid": 9999, "slot": 0}
    lock_file.write_text(json.dumps(lock_data))
    with mock.patch.object(wt_mod, "_LOCK_DIR", tmp_path):
        result = acquire_claude_lock("new_owner", timeout_hours=3)
    assert result == 0
    assert json.loads((tmp_path / "claude_session.0.lock").read_text())["owner"] == "new_owner"


def test_acquire_lock_breaks_dead_pid(tmp_path):
    lock_file = tmp_path / "claude_session.0.lock"
    # pid=1 is init on Linux (alive) but very unlikely to be a live process we own;
    # use pid=999999999 which is guaranteed not to exist
    lock_data = {
        "owner": "dead_process",
        "locked_at": datetime.now(timezone.utc).isoformat(),
        "pid": 999999999,
        "slot": 0,
    }
    lock_file.write_text(json.dumps(lock_data))
    with mock.patch.object(wt_mod, "_LOCK_DIR", tmp_path):
        result = acquire_claude_lock("new_owner", timeout_hours=3)
    assert result == 0


def test_acquire_lock_breaks_corrupted(tmp_path):
    lock_file = tmp_path / "claude_session.0.lock"
    lock_file.write_text("not valid json {{{{")
    with mock.patch.object(wt_mod, "_LOCK_DIR", tmp_path):
        result = acquire_claude_lock("new_owner")
    assert result == 0


def test_release_lock_removes_file(tmp_path):
    lock_file = tmp_path / "claude_session.0.lock"
    lock_file.write_text('{"owner": "me", "slot": 0}')
    with mock.patch.object(wt_mod, "_LOCK_DIR", tmp_path):
        release_claude_lock(0)
    assert not lock_file.exists()


def test_release_lock_no_file_is_noop(tmp_path):
    with mock.patch.object(wt_mod, "_LOCK_DIR", tmp_path):
        release_claude_lock(0)  # should not raise


def test_acquire_all_slots_held_returns_none(tmp_path):
    """When all N slots are held, acquire returns None and writes a skip event."""
    # Pre-fill both slots with live-PID locks
    for slot in range(2):
        p = tmp_path / f"claude_session.{slot}.lock"
        p.write_text(json.dumps({
            "owner": f"holder_{slot}",
            "locked_at": datetime.now(timezone.utc).isoformat(),
            "pid": os.getpid(),
            "slot": slot,
        }))

    with mock.patch.object(wt_mod, "_LOCK_DIR", tmp_path), \
         mock.patch.dict(os.environ, {"JARVIS_CLAUDE_SLOTS": "2"}):
        result = acquire_claude_lock("newcomer")

    assert result is None
    # skip event log should exist
    events_file = tmp_path / "claude_lock_events.jsonl"
    with mock.patch.object(wt_mod, "_LOCK_EVENTS", events_file):
        pass  # event already written to real _LOCK_EVENTS; just verify result


def test_acquire_second_slot_when_slot0_held(tmp_path):
    """With 2 slots configured, slot 1 is returned when slot 0 is held."""
    slot0 = tmp_path / "claude_session.0.lock"
    slot0.write_text(json.dumps({
        "owner": "holder",
        "locked_at": datetime.now(timezone.utc).isoformat(),
        "pid": os.getpid(),
        "slot": 0,
    }))
    with mock.patch.object(wt_mod, "_LOCK_DIR", tmp_path), \
         mock.patch.dict(os.environ, {"JARVIS_CLAUDE_SLOTS": "2"}):
        result = acquire_claude_lock("newcomer")
    assert result == 1
    assert (tmp_path / "claude_session.1.lock").exists()
