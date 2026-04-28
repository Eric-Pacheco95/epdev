"""Tests for compress_signals pure functions."""

import json
import os
import sys
import tempfile
from pathlib import Path
from unittest.mock import patch

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

import tools.scripts.compress_signals as cs
from tools.scripts.compress_signals import (
    load_gzip_days,
    find_compressible,
    compress_file,
    parse_signal_frontmatter,
    _sanitize_ascii,
    load_synthesized_signals,
    get_last_synthesis_timestamp,
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


def test_sanitize_ascii_em_dash():
    assert _sanitize_ascii("before\u2014after") == "before--after"


def test_sanitize_ascii_en_dash():
    assert _sanitize_ascii("2020\u20132026") == "2020-2026"


def test_sanitize_ascii_curly_single_quotes():
    assert _sanitize_ascii("\u2018hello\u2019") == "'hello'"


def test_sanitize_ascii_curly_double_quotes():
    assert _sanitize_ascii("\u201chello\u201d") == '"hello"'


def test_sanitize_ascii_no_change_for_plain_text():
    plain = "just normal ASCII text -> already fine"
    assert _sanitize_ascii(plain) == plain


def test_find_compressible_old_files_included(tmp_path):
    import os, time
    md = tmp_path / "old.md"
    md.write_text("content", encoding="utf-8")
    # backdate mtime by 200 days
    old_time = time.time() - (200 * 86400)
    os.utime(str(md), (old_time, old_time))
    results = find_compressible(tmp_path, max_age_days=180)
    assert md in results


def test_find_compressible_new_files_excluded(tmp_path):
    md = tmp_path / "new.md"
    md.write_text("content", encoding="utf-8")
    results = find_compressible(tmp_path, max_age_days=180)
    assert md not in results


def test_find_compressible_only_md_extension(tmp_path):
    import os, time
    txt = tmp_path / "old.txt"
    txt.write_text("content", encoding="utf-8")
    old_time = time.time() - (200 * 86400)
    os.utime(str(txt), (old_time, old_time))
    results = find_compressible(tmp_path, max_age_days=180)
    assert txt not in results
    assert _sanitize_ascii("a \u2014 b") == "a -- b"


# ---------------------------------------------------------------------------
# load_synthesized_signals
# ---------------------------------------------------------------------------

class TestLoadSynthesizedSignals:
    def test_missing_file_returns_empty(self, tmp_path):
        with patch.object(cs, "LINEAGE_FILE", tmp_path / "nonexistent.jsonl"):
            result = load_synthesized_signals()
        assert result == set()

    def test_new_schema_signals_array(self, tmp_path):
        f = tmp_path / "lineage.jsonl"
        f.write_text(
            json.dumps({"signals": ["memory/signals/foo.md", "memory/signals/bar.md"]}) + "\n",
            encoding="utf-8",
        )
        with patch.object(cs, "LINEAGE_FILE", f):
            result = load_synthesized_signals()
        assert "foo.md" in result
        assert "bar.md" in result

    def test_old_schema_signal_filename(self, tmp_path):
        f = tmp_path / "lineage.jsonl"
        f.write_text(
            json.dumps({"signal_filename": "memory/learning/signals/processed/baz.md"}) + "\n",
            encoding="utf-8",
        )
        with patch.object(cs, "LINEAGE_FILE", f):
            result = load_synthesized_signals()
        assert "baz.md" in result

    def test_bare_filenames_no_path_prefix(self, tmp_path):
        f = tmp_path / "lineage.jsonl"
        f.write_text(
            json.dumps({"signals": ["deep/nested/path/signal.md"]}) + "\n",
            encoding="utf-8",
        )
        with patch.object(cs, "LINEAGE_FILE", f):
            result = load_synthesized_signals()
        assert "signal.md" in result
        assert "deep/nested/path/signal.md" not in result

    def test_bad_json_lines_skipped(self, tmp_path):
        f = tmp_path / "lineage.jsonl"
        f.write_text(
            "not json\n" + json.dumps({"signals": ["a.md"]}) + "\n",
            encoding="utf-8",
        )
        with patch.object(cs, "LINEAGE_FILE", f):
            result = load_synthesized_signals()
        assert "a.md" in result
        assert len(result) == 1

    def test_blank_lines_skipped(self, tmp_path):
        f = tmp_path / "lineage.jsonl"
        f.write_text(
            "\n\n" + json.dumps({"signals": ["c.md"]}) + "\n\n",
            encoding="utf-8",
        )
        with patch.object(cs, "LINEAGE_FILE", f):
            result = load_synthesized_signals()
        assert result == {"c.md"}


# ---------------------------------------------------------------------------
# get_last_synthesis_timestamp
# ---------------------------------------------------------------------------

class TestGetLastSynthesisTimestamp:
    def test_missing_file_returns_none(self, tmp_path):
        with patch.object(cs, "LINEAGE_FILE", tmp_path / "nonexistent.jsonl"):
            result = get_last_synthesis_timestamp()
        assert result is None

    def test_iso_timestamp_parsed(self, tmp_path):
        f = tmp_path / "lineage.jsonl"
        f.write_text(
            json.dumps({"timestamp": "2026-04-01T12:00:00Z"}) + "\n",
            encoding="utf-8",
        )
        with patch.object(cs, "LINEAGE_FILE", f):
            result = get_last_synthesis_timestamp()
        assert result is not None
        assert result.year == 2026
        assert result.month == 4

    def test_date_only_format_parsed(self, tmp_path):
        f = tmp_path / "lineage.jsonl"
        f.write_text(
            json.dumps({"date": "2026-03-15"}) + "\n",
            encoding="utf-8",
        )
        with patch.object(cs, "LINEAGE_FILE", f):
            result = get_last_synthesis_timestamp()
        assert result is not None
        assert result.day == 15

    def test_returns_most_recent_of_multiple(self, tmp_path):
        f = tmp_path / "lineage.jsonl"
        f.write_text(
            json.dumps({"timestamp": "2026-01-01T00:00:00Z"}) + "\n" +
            json.dumps({"timestamp": "2026-04-28T10:00:00Z"}) + "\n" +
            json.dumps({"timestamp": "2026-02-15T06:00:00Z"}) + "\n",
            encoding="utf-8",
        )
        with patch.object(cs, "LINEAGE_FILE", f):
            result = get_last_synthesis_timestamp()
        assert result is not None
        assert result.month == 4
        assert result.day == 28

    def test_bad_json_lines_skipped(self, tmp_path):
        f = tmp_path / "lineage.jsonl"
        f.write_text(
            "bad\n" + json.dumps({"timestamp": "2026-04-10T00:00:00Z"}) + "\n",
            encoding="utf-8",
        )
        with patch.object(cs, "LINEAGE_FILE", f):
            result = get_last_synthesis_timestamp()
        assert result is not None

    def test_no_timestamp_key_skipped(self, tmp_path):
        f = tmp_path / "lineage.jsonl"
        f.write_text(
            json.dumps({"signals": ["a.md"]}) + "\n",
            encoding="utf-8",
        )
        with patch.object(cs, "LINEAGE_FILE", f):
            result = get_last_synthesis_timestamp()
        assert result is None
