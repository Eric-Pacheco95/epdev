"""Tests for hook_stop.py -- _slugify and _unique_path helpers."""

import tempfile
from pathlib import Path

from tools.scripts.hook_stop import _slugify, _unique_path


def test_slugify_basic():
    assert _slugify("Hello World") == "hello-world"


def test_slugify_special_chars():
    assert _slugify("Fix: auth/login bug!") == "fix-auth-login-bug"


def test_slugify_empty():
    assert _slugify("") == "session-end"


def test_slugify_only_special():
    assert _slugify("!!!") == "session-end"


def test_slugify_truncates_at_60():
    long_title = "a" * 80
    result = _slugify(long_title)
    assert len(result) <= 60


def test_slugify_strips_leading_trailing_hyphens():
    result = _slugify("  --hello--  ")
    assert not result.startswith("-")
    assert not result.endswith("-")


def test_unique_path_no_conflict(tmp_path):
    path = _unique_path(tmp_path, "mysession")
    assert path == tmp_path / "mysession.md"


def test_unique_path_with_conflict(tmp_path):
    (tmp_path / "mysession.md").write_text("existing")
    path = _unique_path(tmp_path, "mysession")
    assert path == tmp_path / "mysession_2.md"


def test_unique_path_multiple_conflicts(tmp_path):
    (tmp_path / "mysession.md").write_text("existing")
    (tmp_path / "mysession_2.md").write_text("existing")
    path = _unique_path(tmp_path, "mysession")
    assert path == tmp_path / "mysession_3.md"
