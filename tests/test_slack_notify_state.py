"""Tests for slack_notify -- dedup, hashing, and state management."""

from slack_notify import _msg_hash, _is_duplicate, _record_message, _DEDUP_WINDOW_S
from datetime import datetime, timezone


def _empty_state():
    return {"date": "2026-03-29", "counts": {"routine": 0, "critical": 0}, "recent": []}


def test_msg_hash_deterministic():
    h1 = _msg_hash("hello world")
    h2 = _msg_hash("hello world")
    assert h1 == h2
    assert len(h1) == 16


def test_msg_hash_different_inputs():
    assert _msg_hash("a") != _msg_hash("b")


def test_is_duplicate_empty_state():
    state = _empty_state()
    assert _is_duplicate(state, "test message") is False


def test_is_duplicate_after_record():
    state = _empty_state()
    _record_message(state, "test message", "routine")
    assert _is_duplicate(state, "test message") is True
    assert _is_duplicate(state, "different message") is False


def test_is_duplicate_expired():
    state = _empty_state()
    # Manually add an old entry
    old_ts = datetime.now(timezone.utc).timestamp() - _DEDUP_WINDOW_S - 100
    state["recent"].append({"hash": _msg_hash("old msg"), "ts": old_ts})
    assert _is_duplicate(state, "old msg") is False


def test_record_message_increments_count():
    state = _empty_state()
    _record_message(state, "msg 1", "routine")
    _record_message(state, "msg 2", "routine")
    _record_message(state, "crit msg", "critical")
    assert state["counts"]["routine"] == 2
    assert state["counts"]["critical"] == 1
    assert len(state["recent"]) == 3
