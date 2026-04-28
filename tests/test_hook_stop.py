"""Tests for hook_stop.py -- _slugify, _unique_path, and _update_signal_count helpers."""

import json
import sys
import tempfile
from pathlib import Path
from unittest.mock import patch

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

import tools.scripts.hook_stop as hs
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


# ---------------------------------------------------------------------------
# _update_signal_count
# ---------------------------------------------------------------------------

def test_update_signal_count_empty_dir(tmp_path):
    signals = tmp_path / "signals"
    signals.mkdir()
    meta = tmp_path / "_signal_meta.json"
    with patch.object(hs, "SIGNALS_DIR", signals), patch.object(hs, "META_PATH", meta):
        count = hs._update_signal_count()
    assert count == 0
    data = json.loads(meta.read_text(encoding="utf-8"))
    assert data["signal_file_count"] == 0


def test_update_signal_count_counts_md_files(tmp_path):
    signals = tmp_path / "signals"
    signals.mkdir()
    (signals / "sig1.md").write_text("s1")
    (signals / "sig2.md").write_text("s2")
    (signals / "not_md.json").write_text("{}")
    meta = tmp_path / "_signal_meta.json"
    with patch.object(hs, "SIGNALS_DIR", signals), patch.object(hs, "META_PATH", meta):
        count = hs._update_signal_count()
    assert count == 2
    data = json.loads(meta.read_text(encoding="utf-8"))
    assert data["signal_file_count"] == 2


def test_update_signal_count_missing_dir_returns_zero(tmp_path):
    signals = tmp_path / "no_signals"
    meta = tmp_path / "_signal_meta.json"
    with patch.object(hs, "SIGNALS_DIR", signals), patch.object(hs, "META_PATH", meta):
        count = hs._update_signal_count()
    assert count == 0


def test_update_signal_count_writes_timestamp(tmp_path):
    signals = tmp_path / "signals"
    signals.mkdir()
    meta = tmp_path / "_signal_meta.json"
    with patch.object(hs, "SIGNALS_DIR", signals), patch.object(hs, "META_PATH", meta):
        hs._update_signal_count()
    data = json.loads(meta.read_text(encoding="utf-8"))
    assert "updated_at_utc" in data
    assert "T" in data["updated_at_utc"]
