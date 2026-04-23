"""Manifest DB writer -- lightweight helpers for writing to jarvis_index.db manifest tables.

Shared by: self_diagnose_wrapper.py, hook_stop.py, hook_events.py, collectors.
Stdlib only. Graceful fallback: all writes silently no-op if DB is unavailable.
"""

from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[2]
_DB_PATH = _REPO_ROOT / "data" / "jarvis_index.db"
_EXPECTED_SCHEMA_VERSION = 1


def _get_conn() -> sqlite3.Connection | None:
    """Get a DB connection, or None if DB is unavailable or version mismatched."""
    if not _DB_PATH.exists():
        return None
    try:
        conn = sqlite3.connect(str(_DB_PATH), timeout=5)
        conn.execute("PRAGMA journal_mode=WAL")
        row = conn.execute(
            "SELECT version FROM schema_version ORDER BY rowid DESC LIMIT 1"
        ).fetchone()
        if row is None or row[0] != _EXPECTED_SCHEMA_VERSION:
            conn.close()
            return None
        return conn
    except (sqlite3.OperationalError, sqlite3.DatabaseError):
        return None


def write_producer_run(
    producer: str,
    run_date: str,
    started_at: str,
    completed_at: str | None = None,
    duration_seconds: float | None = None,
    status: str = "unknown",
    exit_code: int | None = None,
    artifact_count: int = 0,
    log_path: str | None = None,
) -> bool:
    """Write a producer_runs row. Returns True on success."""
    conn = _get_conn()
    if conn is None:
        return False
    try:
        conn.execute(
            """INSERT OR IGNORE INTO producer_runs
               (producer, run_date, started_at, completed_at, duration_seconds,
                status, exit_code, artifact_count, log_path)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (producer, run_date, started_at, completed_at, duration_seconds,
             status, exit_code, artifact_count, log_path),
        )
        conn.commit()
        conn.execute("PRAGMA wal_checkpoint(TRUNCATE)")
        return True
    except (sqlite3.OperationalError, sqlite3.IntegrityError):
        return False
    finally:
        conn.close()


def write_session_cost(
    session_id: str,
    date: str,
    session_type: str = "interactive",
    duration_seconds: float | None = None,
    input_tokens: int | None = None,
    output_tokens: int | None = None,
    cache_read_tokens: int | None = None,
    cost_usd: float | None = None,
    tools_used: int = 0,
    skills_invoked: list[str] | None = None,
) -> bool:
    """Write a session_costs row. Returns True on success."""
    conn = _get_conn()
    if conn is None:
        return False
    try:
        skills_json = json.dumps(skills_invoked) if skills_invoked else None
        conn.execute(
            """INSERT OR IGNORE INTO session_costs
               (session_id, date, session_type, input_tokens, output_tokens,
                cache_read_tokens, cost_usd, duration_seconds, tools_used, skills_invoked)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (session_id, date, session_type, input_tokens, output_tokens,
             cache_read_tokens, cost_usd, duration_seconds, tools_used, skills_json),
        )
        conn.commit()
        conn.execute("PRAGMA wal_checkpoint(TRUNCATE)")
        return True
    except (sqlite3.OperationalError, sqlite3.IntegrityError):
        return False
    finally:
        conn.close()


def write_skill_usage(
    session_id: str,
    skill_name: str,
    invoked_at: str | None = None,
) -> bool:
    """Write a skill_usage row. Returns True on success."""
    conn = _get_conn()
    if conn is None:
        return False
    if invoked_at is None:
        invoked_at = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    date = invoked_at[:10]
    try:
        conn.execute(
            """INSERT INTO skill_usage (session_id, skill_name, invoked_at, date)
               VALUES (?, ?, ?, ?)""",
            (session_id, skill_name, invoked_at, date),
        )
        conn.commit()
        conn.execute("PRAGMA wal_checkpoint(TRUNCATE)")
        return True
    except (sqlite3.OperationalError, sqlite3.IntegrityError):
        return False
    finally:
        conn.close()


def write_lineage(
    signal_filename: str,
    synthesis_filename: str,
    date: str,
) -> bool:
    """Write a lineage row. Returns True on success."""
    conn = _get_conn()
    if conn is None:
        return False
    try:
        conn.execute(
            """INSERT OR IGNORE INTO lineage
               (signal_filename, synthesis_filename, date) VALUES (?, ?, ?)""",
            (signal_filename, synthesis_filename, date),
        )
        conn.commit()
        conn.execute("PRAGMA wal_checkpoint(TRUNCATE)")
        return True
    except (sqlite3.OperationalError, sqlite3.IntegrityError):
        return False
    finally:
        conn.close()


def query_producer_health(max_age_hours: float = 26) -> list[dict]:
    """Query producer_runs for stale or failed producers.
    Returns list of {'producer', 'last_run', 'last_status', 'hours_ago', 'issue'}.

    Each producer is evaluated on the row with the latest ``started_at`` only.
    (Older ``SELECT ... GROUP BY producer`` picked an arbitrary ``status`` for
    that group in SQLite, so a newer ``success`` could still look ``failed``.)
    """
    conn = _get_conn()
    if conn is None:
        return []
    try:
        now = datetime.now(timezone.utc).replace(tzinfo=None)
        rows = conn.execute(
            """
            SELECT producer, started_at AS last_run, status
            FROM (
                SELECT producer, started_at, status,
                       ROW_NUMBER() OVER (
                           PARTITION BY producer
                           ORDER BY started_at DESC, rowid DESC
                       ) AS rn
                FROM producer_runs
            )
            WHERE rn = 1
            """
        ).fetchall()
        issues = []
        for producer, last_run, status in rows:
            if not last_run:
                continue
            try:
                # Strip timezone info to produce naive-UTC for consistent comparison
                clean = last_run.replace("Z", "").replace("+00:00", "")
                last_dt = datetime.fromisoformat(clean)
            except ValueError:
                continue
            hours_ago = (now - last_dt).total_seconds() / 3600
            issue = None
            if hours_ago > max_age_hours:
                issue = "stale"
            if status == "failure":
                issue = "failed"
            if issue:
                issues.append({
                    "producer": producer,
                    "last_run": last_run,
                    "last_status": status,
                    "hours_ago": round(hours_ago, 1),
                    "issue": issue,
                })
        return issues
    except sqlite3.OperationalError:
        return []
    finally:
        conn.close()
