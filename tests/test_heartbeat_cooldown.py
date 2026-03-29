"""Tests for jarvis_heartbeat cooldown logic."""

import sys
from pathlib import Path
from datetime import datetime, timedelta, timezone

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

from tools.scripts.jarvis_heartbeat import _is_cooled_down


def test_cooled_down_no_previous():
    assert _is_cooled_down("some_metric", {}, 60) is True


def test_cooled_down_enough_time_passed():
    old = (datetime.now(timezone.utc) - timedelta(minutes=120)).strftime("%Y-%m-%dT%H:%M:%SZ")
    state = {"my_metric": old}
    assert _is_cooled_down("my_metric", state, 60) is True


def test_not_cooled_down_recent():
    recent = (datetime.now(timezone.utc) - timedelta(minutes=5)).strftime("%Y-%m-%dT%H:%M:%SZ")
    state = {"my_metric": recent}
    assert _is_cooled_down("my_metric", state, 60) is False


def test_cooled_down_invalid_timestamp():
    state = {"my_metric": "not-a-timestamp"}
    assert _is_cooled_down("my_metric", state, 60) is True


def test_cooled_down_different_metric():
    recent = (datetime.now(timezone.utc) - timedelta(minutes=5)).strftime("%Y-%m-%dT%H:%M:%SZ")
    state = {"other_metric": recent}
    # my_metric has no entry -> cooled down
    assert _is_cooled_down("my_metric", state, 60) is True
