"""Unit tests for tools/scripts/jarvis_index.py pure helpers."""

import sqlite3
import sys
import tempfile
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from tools.scripts.jarvis_index import (
    _parse_signal_frontmatter,
    _parse_producer_from_logname,
    _init_db, _is_indexed, _mark_indexed,
    _PRODUCER_MAP,
)


class TestParseProducerFromLogname:
    def test_heartbeat_prefix(self):
        assert _parse_producer_from_logname("heartbeat_2026-03-29") == "heartbeat"

    def test_overnight_prefix(self):
        assert _parse_producer_from_logname("overnight_2026-04-01") == "overnight"

    def test_dispatcher_prefix(self):
        assert _parse_producer_from_logname("dispatcher_2026-04-10") == "dispatcher"

    def test_morning_feed_prefix(self):
        assert _parse_producer_from_logname("morning_feed_2026-04-15") == "morning_feed"

    def test_unknown_prefix_returns_none(self):
        assert _parse_producer_from_logname("unknown_2026-04-01") is None

    def test_empty_string_returns_none(self):
        assert _parse_producer_from_logname("") is None

    def test_prefix_only_no_date_returns_none(self):
        # Must have prefix + "_" for a match; bare prefix alone shouldn't match unless
        # the log name starts with prefix+"_"
        assert _parse_producer_from_logname("heartbeat") is None

    def test_all_known_producers(self):
        for prefix in _PRODUCER_MAP:
            result = _parse_producer_from_logname(f"{prefix}_2026-01-01")
            assert result == prefix, f"Expected '{prefix}', got '{result}'"


class TestParseSignalFrontmatter:
    def _write_tmp(self, content: str, filename: str = "2026-04-24_test.md") -> Path:
        tmp_dir = Path(tempfile.mkdtemp())
        p = tmp_dir / filename
        p.write_text(content, encoding="utf-8")
        return p

    def test_full_frontmatter_parsed(self):
        content = (
            "# Signal: Harness tooling improved\n"
            "- Date: 2026-04-10\n"
            "- Rating: 4\n"
            "- Category: ai-infra\n"
            "- Source: autonomous\n"
            "\nBody text here.\n"
        )
        p = self._write_tmp(content)
        meta = _parse_signal_frontmatter(p)
        assert meta is not None
        assert meta["title"] == "Harness tooling improved"
        assert meta["date"] == "2026-04-10"
        assert meta["rating"] == 4
        assert meta["category"] == "ai-infra"
        assert meta["source"] == "autonomous"

    def test_date_fallback_from_filename(self):
        content = "# Signal: Title only\n\nNo date field.\n"
        p = self._write_tmp(content, filename="2026-03-15_some-signal.md")
        meta = _parse_signal_frontmatter(p)
        assert meta is not None
        assert meta["date"] == "2026-03-15"

    def test_returns_none_without_date(self):
        content = "# Signal: No date anywhere\n\nNo date field.\n"
        # Filename doesn't have a date prefix
        p = self._write_tmp(content, filename="no-date-signal.md")
        meta = _parse_signal_frontmatter(p)
        assert meta is None

    def test_lowercase_field_names_accepted(self):
        content = (
            "# signal: Lowercase signal header\n"
            "- date: 2026-04-12\n"
            "- rating: 3\n"
            "- category: crypto\n"
            "- source: manual\n"
        )
        p = self._write_tmp(content)
        meta = _parse_signal_frontmatter(p)
        assert meta is not None
        assert meta["title"] == "Lowercase signal header"
        assert meta["rating"] == 3

    def test_invalid_rating_skipped(self):
        content = (
            "# Signal: Bad rating\n"
            "- Date: 2026-04-11\n"
            "- Rating: not-a-number\n"
        )
        p = self._write_tmp(content)
        meta = _parse_signal_frontmatter(p)
        assert meta is not None
        assert meta["rating"] is None

    def test_default_source_is_manual(self):
        content = "# Signal: No source\n- Date: 2026-04-13\n"
        p = self._write_tmp(content)
        meta = _parse_signal_frontmatter(p)
        assert meta is not None
        assert meta["source"] == "manual"

    def test_nonexistent_file_returns_none(self):
        meta = _parse_signal_frontmatter(Path("/nonexistent/path/signal.md"))
        assert meta is None


# ---------------------------------------------------------------------------
# _init_db / _is_indexed / _mark_indexed
# ---------------------------------------------------------------------------

def _make_conn() -> sqlite3.Connection:
    conn = sqlite3.connect(":memory:")
    _init_db(conn)
    return conn


class TestInitDb:
    def test_creates_documents_table(self):
        conn = _make_conn()
        tables = {r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()}
        assert "documents" in tables

    def test_creates_indexed_files_table(self):
        conn = _make_conn()
        tables = {r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()}
        assert "indexed_files" in tables

    def test_idempotent_double_init(self):
        conn = _make_conn()
        _init_db(conn)  # should not raise


class TestIsIndexedMarkIndexed:
    def test_unknown_path_not_indexed(self):
        conn = _make_conn()
        assert _is_indexed(conn, "/some/path.md", 123456) is False

    def test_marked_path_is_indexed(self):
        conn = _make_conn()
        _mark_indexed(conn, "/some/path.md", 999)
        conn.commit()
        assert _is_indexed(conn, "/some/path.md", 999) is True

    def test_different_mtime_not_indexed(self):
        conn = _make_conn()
        _mark_indexed(conn, "/path.md", 100)
        conn.commit()
        assert _is_indexed(conn, "/path.md", 200) is False

    def test_mark_indexed_upserts(self):
        conn = _make_conn()
        _mark_indexed(conn, "/path.md", 100)
        _mark_indexed(conn, "/path.md", 200)
        conn.commit()
        assert _is_indexed(conn, "/path.md", 200) is True
        assert _is_indexed(conn, "/path.md", 100) is False
