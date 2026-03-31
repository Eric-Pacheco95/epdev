"""Pytest tests for tools/scripts/slack_notify.py — _msg_hash, _is_duplicate, _record_message."""

import sys
import time
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from tools.scripts.slack_notify import (
    _msg_hash,
    _is_duplicate,
    _record_message,
    _DEDUP_WINDOW_S,
    _DAILY_CAPS,
    _SEVERITY_CHANNEL,
    EPDEV,
    CRITICAL,
)


class TestMsgHash:
    def test_deterministic(self):
        assert _msg_hash("hello") == _msg_hash("hello")

    def test_different_inputs(self):
        assert _msg_hash("hello") != _msg_hash("world")

    def test_length(self):
        assert len(_msg_hash("test")) == 16

    def test_hex_chars(self):
        h = _msg_hash("test")
        assert all(c in "0123456789abcdef" for c in h)


class TestIsDuplicate:
    def test_no_recent(self):
        state = {"recent": []}
        assert _is_duplicate(state, "hello") is False

    def test_same_message_recent(self):
        h = _msg_hash("hello")
        state = {"recent": [{"hash": h, "ts": time.time()}]}
        assert _is_duplicate(state, "hello") is True

    def test_different_message(self):
        h = _msg_hash("other")
        state = {"recent": [{"hash": h, "ts": time.time()}]}
        assert _is_duplicate(state, "hello") is False

    def test_expired_entry_cleaned(self):
        h = _msg_hash("hello")
        old_ts = time.time() - _DEDUP_WINDOW_S - 100
        state = {"recent": [{"hash": h, "ts": old_ts}]}
        assert _is_duplicate(state, "hello") is False
        assert len(state["recent"]) == 0  # expired entry removed


class TestRecordMessage:
    def test_increments_count(self):
        state = {"counts": {"routine": 0, "critical": 0}, "recent": []}
        _record_message(state, "test", "routine")
        assert state["counts"]["routine"] == 1

    def test_adds_to_recent(self):
        state = {"counts": {"routine": 0}, "recent": []}
        _record_message(state, "test", "routine")
        assert len(state["recent"]) == 1
        assert state["recent"][0]["hash"] == _msg_hash("test")

    def test_multiple_records(self):
        state = {"counts": {"routine": 0}, "recent": []}
        _record_message(state, "msg1", "routine")
        _record_message(state, "msg2", "routine")
        assert state["counts"]["routine"] == 2
        assert len(state["recent"]) == 2


class TestConstants:
    def test_severity_channel_mapping(self):
        assert _SEVERITY_CHANNEL["routine"] == EPDEV
        assert _SEVERITY_CHANNEL["critical"] == CRITICAL

    def test_daily_caps_defined(self):
        assert _DAILY_CAPS["routine"] == 20
        assert _DAILY_CAPS["critical"] == 5

    def test_dedup_window(self):
        assert _DEDUP_WINDOW_S == 3600
