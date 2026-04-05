"""Tests for jarvis_index.py -- pure helper functions."""

import tempfile
import os
from pathlib import Path

from tools.scripts.jarvis_index import _parse_signal_frontmatter, _parse_producer_from_logname


# --- _parse_signal_frontmatter ---

def _write_signal(tmp_path, filename, content):
    p = tmp_path / filename
    p.write_text(content, encoding="utf-8")
    return p


def test_parse_signal_full_frontmatter(tmp_path):
    content = (
        "# Signal: Test discovery\n"
        "- Date: 2026-04-01\n"
        "- Rating: 7\n"
        "- Category: codebase_health\n"
        "- Source: session\n"
    )
    path = _write_signal(tmp_path, "2026-04-01_test.md", content)
    meta = _parse_signal_frontmatter(path)
    assert meta is not None
    assert meta["title"] == "Test discovery"
    assert meta["date"] == "2026-04-01"
    assert meta["rating"] == 7
    assert meta["category"] == "codebase_health"
    assert meta["source"] == "session"


def test_parse_signal_date_from_filename(tmp_path):
    content = "# Signal: No explicit date\n"
    path = _write_signal(tmp_path, "2026-03-15_nodateheader.md", content)
    meta = _parse_signal_frontmatter(path)
    assert meta is not None
    assert meta["date"] == "2026-03-15"


def test_parse_signal_no_date_returns_none(tmp_path):
    content = "# Signal: Missing date\n- Rating: 5\n"
    path = _write_signal(tmp_path, "nodatefile.md", content)
    meta = _parse_signal_frontmatter(path)
    assert meta is None


def test_parse_signal_missing_file(tmp_path):
    path = tmp_path / "nonexistent.md"
    meta = _parse_signal_frontmatter(path)
    assert meta is None


def test_parse_signal_invalid_rating(tmp_path):
    content = "# Signal: Bad rating\n- Date: 2026-04-01\n- Rating: notanumber\n"
    path = _write_signal(tmp_path, "2026-04-01_bad.md", content)
    meta = _parse_signal_frontmatter(path)
    assert meta is not None
    assert meta["rating"] is None


def test_parse_signal_lowercase_keys(tmp_path):
    content = "# signal: lowercase\n- date: 2026-04-02\n- rating: 8\n"
    path = _write_signal(tmp_path, "2026-04-02_lower.md", content)
    meta = _parse_signal_frontmatter(path)
    assert meta is not None
    assert meta["title"] == "lowercase"
    assert meta["date"] == "2026-04-02"
    assert meta["rating"] == 8


# --- _parse_producer_from_logname ---

def test_parse_producer_heartbeat():
    result = _parse_producer_from_logname("heartbeat_2026-03-29")
    assert result == "heartbeat"


def test_parse_producer_no_match():
    result = _parse_producer_from_logname("unknown_producer_2026-01-01")
    assert result is None


def test_parse_producer_no_underscore():
    result = _parse_producer_from_logname("heartbeat")
    assert result is None
