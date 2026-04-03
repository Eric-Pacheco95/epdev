"""Tests for compress_signals pure functions."""

import json
import os
import tempfile
from pathlib import Path

from tools.scripts.compress_signals import (
    load_gzip_days,
    find_compressible,
    compress_file,
    parse_signal_frontmatter,
    _sanitize_ascii,
)


def test_load_gzip_days_default():
    """Returns default 180 when config file doesn't exist."""
    assert load_gzip_days(Path("/nonexistent/config.json")) == 180


def test_load_gzip_days_from_config():
    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
        json.dump({"retention": {"gzip_after_days": 90}}, f)
        f.flush()
        result = load_gzip_days(Path(f.name))
    os.unlink(f.name)
    assert result == 90


def test_load_gzip_days_bad_json():
    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
        f.write("not json")
        f.flush()
        result = load_gzip_days(Path(f.name))
    os.unlink(f.name)
    assert result == 180


def test_find_compressible_empty_dir():
    with tempfile.TemporaryDirectory() as tmpdir:
        result = find_compressible(Path(tmpdir), 30)
        assert result == []


def test_find_compressible_nonexistent():
    result = find_compressible(Path("/nonexistent/dir"), 30)
    assert result == []


def test_compress_file():
    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".md", delete=False, dir=tempfile.gettempdir()
    ) as f:
        f.write("test signal content")
        f.flush()
        p = Path(f.name)

    gz_path = compress_file(p)
    assert gz_path.suffix == ".gz"
    assert gz_path.exists()
    assert not p.exists()
    gz_path.unlink()


def test_parse_signal_frontmatter_with_frontmatter():
    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".md", delete=False, dir=tempfile.gettempdir()
    ) as f:
        f.write("---\ncategory: pattern\nrating: 7\n---\n\nSignal body")
        f.flush()
        p = Path(f.name)

    meta = parse_signal_frontmatter(p)
    assert meta["category"] == "pattern"
    assert meta["rating"] == 7
    p.unlink()


def test_parse_signal_frontmatter_infer_category():
    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".md", delete=False,
        dir=tempfile.gettempdir(), prefix="failure_"
    ) as f:
        f.write("No frontmatter here")
        f.flush()
        p = Path(f.name)

    meta = parse_signal_frontmatter(p)
    assert meta["category"] == "failure"
    p.unlink()


def test_parse_signal_frontmatter_uncategorized():
    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".md", delete=False,
        dir=tempfile.gettempdir(), prefix="misc_"
    ) as f:
        f.write("No frontmatter")
        f.flush()
        p = Path(f.name)

    meta = parse_signal_frontmatter(p)
    assert meta["category"] == "uncategorized"
    p.unlink()


def test_parse_signal_frontmatter_unreadable():
    meta = parse_signal_frontmatter(Path("/nonexistent/signal.md"))
    assert "error" in meta


def test_sanitize_ascii_arrows():
    assert _sanitize_ascii("\u2192 next") == "-> next"
    assert _sanitize_ascii("a \u2014 b") == "a -- b"
