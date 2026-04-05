"""Tests for lib/worktree.py -- acquire_claude_lock and release_claude_lock."""

import json
from datetime import datetime, timezone, timedelta
from unittest import mock

import tools.scripts.lib.worktree as wt_mod
from tools.scripts.lib.worktree import acquire_claude_lock, release_claude_lock


def test_acquire_lock_when_free(tmp_path):
    lock_file = tmp_path / "claude_session.lock"
    with mock.patch.object(wt_mod, "_CLAUDE_LOCK", lock_file):
        result = acquire_claude_lock("test_owner")
    assert result is True
    assert lock_file.exists()
    data = json.loads(lock_file.read_text())
    assert data["owner"] == "test_owner"


def test_acquire_lock_already_held(tmp_path):
    lock_file = tmp_path / "claude_session.lock"
    # Write a fresh lock (age << timeout)
    lock_data = {
        "owner": "other_process",
        "locked_at": datetime.now(timezone.utc).isoformat(),
        "pid": 12345,
    }
    lock_file.write_text(json.dumps(lock_data))
    with mock.patch.object(wt_mod, "_CLAUDE_LOCK", lock_file):
        result = acquire_claude_lock("new_owner")
    assert result is False


def test_acquire_lock_breaks_stale(tmp_path):
    lock_file = tmp_path / "claude_session.lock"
    # Write a stale lock (age > timeout)
    stale_time = datetime.now(timezone.utc) - timedelta(hours=5)
    lock_data = {"owner": "crashed_process", "locked_at": stale_time.isoformat(), "pid": 9999}
    lock_file.write_text(json.dumps(lock_data))
    with mock.patch.object(wt_mod, "_CLAUDE_LOCK", lock_file):
        result = acquire_claude_lock("new_owner", timeout_hours=3)
    assert result is True
    assert json.loads(lock_file.read_text())["owner"] == "new_owner"


def test_acquire_lock_breaks_corrupted(tmp_path):
    lock_file = tmp_path / "claude_session.lock"
    lock_file.write_text("not valid json {{{{")
    with mock.patch.object(wt_mod, "_CLAUDE_LOCK", lock_file):
        result = acquire_claude_lock("new_owner")
    assert result is True


def test_release_lock_removes_file(tmp_path):
    lock_file = tmp_path / "claude_session.lock"
    lock_file.write_text('{"owner": "me"}')
    with mock.patch.object(wt_mod, "_CLAUDE_LOCK", lock_file):
        release_claude_lock()
    assert not lock_file.exists()


def test_release_lock_no_file_is_noop(tmp_path):
    lock_file = tmp_path / "claude_session.lock"
    with mock.patch.object(wt_mod, "_CLAUDE_LOCK", lock_file):
        release_claude_lock()  # should not raise
