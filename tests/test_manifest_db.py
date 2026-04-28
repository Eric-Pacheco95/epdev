"""Tests for manifest_db.py -- graceful-fallback and write paths."""

import sqlite3
import tempfile
from pathlib import Path
from unittest import mock

import tools.scripts.manifest_db as mdb


def test_get_conn_no_db(tmp_path):
    with mock.patch.object(mdb, "_DB_PATH", tmp_path / "nonexistent.db"):
        assert mdb._get_conn() is None


def test_write_producer_run_no_db(tmp_path):
    with mock.patch.object(mdb, "_DB_PATH", tmp_path / "nonexistent.db"):
        result = mdb.write_producer_run(
            producer="test", run_date="2026-01-01",
            started_at="2026-01-01T00:00:00Z",
        )
    assert result is False


def test_write_session_cost_no_db(tmp_path):
    with mock.patch.object(mdb, "_DB_PATH", tmp_path / "nonexistent.db"):
        result = mdb.write_session_cost(
            session_id="abc123", date="2026-01-01"
        )
    assert result is False


def test_write_skill_usage_no_db(tmp_path):
    with mock.patch.object(mdb, "_DB_PATH", tmp_path / "nonexistent.db"):
        result = mdb.write_skill_usage(session_id="abc123", skill_name="commit")
    assert result is False


def test_write_lineage_no_db(tmp_path):
    with mock.patch.object(mdb, "_DB_PATH", tmp_path / "nonexistent.db"):
        result = mdb.write_lineage(
            signal_filename="sig.md",
            synthesis_filename="synth.md",
            date="2026-01-01",
        )
    assert result is False


def test_query_producer_health_no_db(tmp_path):
    with mock.patch.object(mdb, "_DB_PATH", tmp_path / "nonexistent.db"):
        result = mdb.query_producer_health()
    assert result == []


def _make_test_db(path: Path) -> None:
    """Create a minimal jarvis_index.db with correct schema for testing."""
    conn = sqlite3.connect(str(path))
    conn.execute("CREATE TABLE schema_version (version INTEGER)")
    conn.execute("INSERT INTO schema_version VALUES (1)")
    conn.execute("""CREATE TABLE producer_runs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        producer TEXT, run_date TEXT, started_at TEXT, completed_at TEXT,
        duration_seconds REAL, status TEXT, exit_code INTEGER,
        artifact_count INTEGER, log_path TEXT,
        UNIQUE(producer, started_at)
    )""")
    conn.execute("""CREATE TABLE session_costs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        session_id TEXT UNIQUE, date TEXT, session_type TEXT,
        input_tokens INTEGER, output_tokens INTEGER,
        cache_read_tokens INTEGER, cost_usd REAL,
        duration_seconds REAL, tools_used INTEGER, skills_invoked TEXT
    )""")
    conn.execute("""CREATE TABLE skill_usage (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        session_id TEXT, skill_name TEXT, invoked_at TEXT, date TEXT
    )""")
    conn.execute("""CREATE TABLE lineage (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        signal_filename TEXT, synthesis_filename TEXT, date TEXT,
        UNIQUE(signal_filename, synthesis_filename)
    )""")
    conn.commit()
    conn.close()


def test_write_producer_run_success(tmp_path):
    db = tmp_path / "jarvis_index.db"
    _make_test_db(db)
    with mock.patch.object(mdb, "_DB_PATH", db):
        result = mdb.write_producer_run(
            producer="test_producer", run_date="2026-01-01",
            started_at="2026-01-01T00:00:00Z", status="success",
        )
    assert result is True


def test_write_session_cost_success(tmp_path):
    db = tmp_path / "jarvis_index.db"
    _make_test_db(db)
    with mock.patch.object(mdb, "_DB_PATH", db):
        result = mdb.write_session_cost(
            session_id="sess-001", date="2026-01-01",
            input_tokens=100, output_tokens=50,
        )
    assert result is True


def test_write_skill_usage_default_timestamp(tmp_path):
    """write_skill_usage should use current UTC time when invoked_at is None."""
    db = tmp_path / "jarvis_index.db"
    _make_test_db(db)
    with mock.patch.object(mdb, "_DB_PATH", db):
        result = mdb.write_skill_usage(session_id="sess-001", skill_name="commit")
    assert result is True


def test_write_lineage_success(tmp_path):
    db = tmp_path / "jarvis_index.db"
    _make_test_db(db)
    with mock.patch.object(mdb, "_DB_PATH", db):
        result = mdb.write_lineage(
            signal_filename="sig-001.md",
            synthesis_filename="synth-2026-01.md",
            date="2026-01-01",
        )
    assert result is True


def test_query_producer_health_stale(tmp_path):
    """query_producer_health returns stale producers older than max_age_hours."""
    db = tmp_path / "jarvis_index.db"
    _make_test_db(db)
    conn = sqlite3.connect(str(db))
    conn.execute(
        "INSERT INTO producer_runs (producer, run_date, started_at, status) "
        "VALUES (?, ?, ?, ?)",
        ("old_producer", "2020-01-01", "2020-01-01T00:00:00Z", "success"),
    )
    conn.commit()
    conn.close()
    with mock.patch.object(mdb, "_DB_PATH", db):
        result = mdb.query_producer_health(max_age_hours=1)
    assert len(result) == 1
    assert result[0]["producer"] == "old_producer"
    assert result[0]["issue"] == "stale"


def test_query_producer_health_failed(tmp_path):
    """query_producer_health flags producers with failure status."""
    db = tmp_path / "jarvis_index.db"
    _make_test_db(db)
    conn = sqlite3.connect(str(db))
    conn.execute(
        "INSERT INTO producer_runs (producer, run_date, started_at, status) "
        "VALUES (?, ?, ?, ?)",
        ("broken_producer", "2020-01-01", "2020-01-01T00:00:00Z", "failure"),
    )
    conn.commit()
    conn.close()
    with mock.patch.object(mdb, "_DB_PATH", db):
        result = mdb.query_producer_health(max_age_hours=99999)
    assert any(r["issue"] == "failed" for r in result)


def test_write_producer_run_normalizes_failed_alias(tmp_path):
    """Writers historically used 'failed' (domain_consolidator) vs 'failure'
    (everyone else) — write path must normalize to canonical 'failure' so the
    reader can match a single string."""
    db = tmp_path / "jarvis_index.db"
    _make_test_db(db)
    with mock.patch.object(mdb, "_DB_PATH", db):
        assert mdb.write_producer_run(
            producer="alias_check", run_date="2026-01-01",
            started_at="2026-01-01T00:00:00Z", status="failed",
        ) is True
    conn = sqlite3.connect(str(db))
    row = conn.execute(
        "SELECT status FROM producer_runs WHERE producer='alias_check'"
    ).fetchone()
    conn.close()
    assert row[0] == "failure"


def test_write_producer_run_unknown_status_falls_back(tmp_path):
    """Unrecognized status strings must not silently corrupt the table — fall
    back to 'unknown' so downstream classifiers stay deterministic."""
    db = tmp_path / "jarvis_index.db"
    _make_test_db(db)
    with mock.patch.object(mdb, "_DB_PATH", db):
        assert mdb.write_producer_run(
            producer="bogus", run_date="2026-01-01",
            started_at="2026-01-01T00:00:00Z", status="weird-value",
        ) is True
    conn = sqlite3.connect(str(db))
    row = conn.execute(
        "SELECT status FROM producer_runs WHERE producer='bogus'"
    ).fetchone()
    conn.close()
    assert row[0] == "unknown"


def test_query_producer_health_recognizes_failed_alias(tmp_path):
    """Defense in depth — even if a future direct-SQL writer skips
    write_producer_run() and inserts the 'failed' alias, the reader still
    classifies it as a failure."""
    db = tmp_path / "jarvis_index.db"
    _make_test_db(db)
    conn = sqlite3.connect(str(db))
    conn.execute(
        "INSERT INTO producer_runs (producer, run_date, started_at, status) "
        "VALUES (?, ?, ?, ?)",
        ("legacy_writer", "2026-01-01", "2026-01-01T00:00:00Z", "failed"),
    )
    conn.commit()
    conn.close()
    with mock.patch.object(mdb, "_DB_PATH", db):
        result = mdb.query_producer_health(max_age_hours=99999)
    assert any(r["producer"] == "legacy_writer" and r["issue"] == "failed"
               for r in result)


def test_query_producer_health_per_producer_cadence_override(tmp_path):
    """domain_consolidator runs weekly (168h) — must not be flagged stale at
    the daily 26h default."""
    db = tmp_path / "jarvis_index.db"
    _make_test_db(db)
    from datetime import datetime, timezone, timedelta
    forty_hours_ago = (datetime.now(timezone.utc) - timedelta(hours=40)).isoformat()
    conn = sqlite3.connect(str(db))
    conn.execute(
        "INSERT INTO producer_runs (producer, run_date, started_at, status) "
        "VALUES (?, ?, ?, ?)",
        ("domain_consolidator", "2026-01-01", forty_hours_ago, "success"),
    )
    conn.commit()
    conn.close()
    with mock.patch.object(mdb, "_DB_PATH", db):
        result = mdb.query_producer_health(max_age_hours=26)
    assert result == [], "weekly producer at 40h must not trip a 26h stale flag"


def test_query_producer_health_status_matches_latest_started_at(tmp_path):
    """Status must come from the latest row per producer, not an arbitrary GROUP BY row."""
    db = tmp_path / "jarvis_index.db"
    _make_test_db(db)
    conn = sqlite3.connect(str(db))
    conn.execute(
        "INSERT INTO producer_runs (producer, run_date, started_at, status) "
        "VALUES (?, ?, ?, ?)",
        ("p1", "2026-01-01", "2026-01-01T00:00:00Z", "failure"),
    )
    conn.execute(
        "INSERT INTO producer_runs (producer, run_date, started_at, status) "
        "VALUES (?, ?, ?, ?)",
        ("p1", "2026-01-02", "2026-01-02T00:00:00Z", "success"),
    )
    conn.commit()
    conn.close()
    with mock.patch.object(mdb, "_DB_PATH", db):
        result = mdb.query_producer_health(max_age_hours=99999)
    assert result == [], "latest run is success and fresh -- expect no issues"

    db2 = tmp_path / "jarvis_index2.db"
    _make_test_db(db2)
    conn2 = sqlite3.connect(str(db2))
    conn2.execute(
        "INSERT INTO producer_runs (producer, run_date, started_at, status) "
        "VALUES (?, ?, ?, ?)",
        ("p2", "2026-01-01", "2026-01-01T00:00:00Z", "success"),
    )
    conn2.execute(
        "INSERT INTO producer_runs (producer, run_date, started_at, status) "
        "VALUES (?, ?, ?, ?)",
        ("p2", "2026-01-02", "2026-01-02T00:00:00Z", "failure"),
    )
    conn2.commit()
    conn2.close()
    with mock.patch.object(mdb, "_DB_PATH", db2):
        result2 = mdb.query_producer_health(max_age_hours=99999)
    assert len(result2) == 1
    assert result2[0]["producer"] == "p2"
    assert result2[0]["issue"] == "failed"
