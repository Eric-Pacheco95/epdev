"""
Jarvis Knowledge Index -- unified full-text search across all Jarvis data.

Uses SQLite FTS5 to index: Claude Code sessions, learning signals, failures,
decisions, security events, and heartbeat logs.

Usage:
    python jarvis_index.py build          # Build/rebuild the full index
    python jarvis_index.py update         # Incremental update (new files only)
    python jarvis_index.py search <query> # Search across all sources
    python jarvis_index.py search <query> --source sessions  # Filter by source
    python jarvis_index.py stats          # Show index statistics
"""

from __future__ import annotations

import argparse
import json
import re as _re
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

# -- Paths -----------------------------------------------------------------

_SCRIPT_DIR = Path(__file__).resolve().parent
_REPO_ROOT = _SCRIPT_DIR.parents[1]
_DB_PATH = _REPO_ROOT / "data" / "jarvis_index.db"

_EXPECTED_SCHEMA_VERSION = 1

_CLAUDE_PROJECTS = Path.home() / ".claude" / "projects"
_SIGNALS_DIR = _REPO_ROOT / "memory" / "learning" / "signals"
_FAILURES_DIR = _REPO_ROOT / "memory" / "learning" / "failures"
_SYNTHESIS_DIR = _REPO_ROOT / "memory" / "learning" / "synthesis"
_DECISIONS_DIR = _REPO_ROOT / "history" / "decisions"
_SECURITY_DIR = _REPO_ROOT / "history" / "security"
_HEARTBEAT_DIR = _REPO_ROOT / "data" / "logs"

# -- Database setup --------------------------------------------------------


def _init_db(conn: sqlite3.Connection) -> None:
    conn.execute("""
        CREATE TABLE IF NOT EXISTS documents (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            source TEXT NOT NULL,
            source_file TEXT NOT NULL,
            timestamp TEXT,
            title TEXT,
            content TEXT NOT NULL,
            indexed_at TEXT NOT NULL
        )
    """)
    conn.execute("""
        CREATE VIRTUAL TABLE IF NOT EXISTS documents_fts USING fts5(
            title, content, source,
            content=documents,
            content_rowid=id,
            tokenize='porter unicode61'
        )
    """)
    # Triggers to keep FTS in sync
    conn.executescript("""
        CREATE TRIGGER IF NOT EXISTS documents_ai AFTER INSERT ON documents BEGIN
            INSERT INTO documents_fts(rowid, title, content, source)
            VALUES (new.id, new.title, new.content, new.source);
        END;
        CREATE TRIGGER IF NOT EXISTS documents_ad AFTER DELETE ON documents BEGIN
            INSERT INTO documents_fts(documents_fts, rowid, title, content, source)
            VALUES ('delete', old.id, old.title, old.content, old.source);
        END;
    """)
    # Track which files have been indexed
    conn.execute("""
        CREATE TABLE IF NOT EXISTS indexed_files (
            source_file TEXT PRIMARY KEY,
            mtime_ns INTEGER NOT NULL,
            indexed_at TEXT NOT NULL
        )
    """)

    # -- Manifest tables (Phase 4E data layer) --------------------------------
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS signals (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            filename TEXT UNIQUE NOT NULL,
            title TEXT,
            date TEXT NOT NULL,
            source TEXT,
            category TEXT,
            rating INTEGER,
            processed INTEGER DEFAULT 0,
            synthesis_id INTEGER,
            deleted_at TEXT,
            created_at TEXT NOT NULL DEFAULT (datetime('now'))
        );
        CREATE INDEX IF NOT EXISTS idx_signals_date ON signals(date);
        CREATE INDEX IF NOT EXISTS idx_signals_source ON signals(source);
        CREATE INDEX IF NOT EXISTS idx_signals_category ON signals(category);
        CREATE INDEX IF NOT EXISTS idx_signals_processed ON signals(processed);

        CREATE TABLE IF NOT EXISTS lineage (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            signal_filename TEXT NOT NULL,
            synthesis_filename TEXT NOT NULL,
            date TEXT NOT NULL,
            UNIQUE(signal_filename, synthesis_filename)
        );

        CREATE TABLE IF NOT EXISTS producer_runs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            producer TEXT NOT NULL,
            run_date TEXT NOT NULL,
            started_at TEXT,
            completed_at TEXT,
            duration_seconds REAL,
            status TEXT NOT NULL DEFAULT 'unknown',
            exit_code INTEGER,
            artifact_count INTEGER DEFAULT 0,
            log_path TEXT,
            UNIQUE(producer, run_date, started_at)
        );
        CREATE INDEX IF NOT EXISTS idx_producer_runs_producer ON producer_runs(producer);
        CREATE INDEX IF NOT EXISTS idx_producer_runs_date ON producer_runs(run_date);
        CREATE INDEX IF NOT EXISTS idx_producer_runs_status ON producer_runs(status);

        CREATE TABLE IF NOT EXISTS session_costs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id TEXT NOT NULL,
            date TEXT NOT NULL,
            session_type TEXT,
            input_tokens INTEGER,
            output_tokens INTEGER,
            cache_read_tokens INTEGER,
            cost_usd REAL,
            duration_seconds REAL,
            tools_used INTEGER DEFAULT 0,
            skills_invoked TEXT,
            UNIQUE(session_id)
        );
        CREATE INDEX IF NOT EXISTS idx_session_costs_date ON session_costs(date);
        CREATE INDEX IF NOT EXISTS idx_session_costs_type ON session_costs(session_type);

        CREATE TABLE IF NOT EXISTS skill_usage (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id TEXT NOT NULL,
            skill_name TEXT NOT NULL,
            invoked_at TEXT NOT NULL,
            date TEXT NOT NULL
        );
        CREATE INDEX IF NOT EXISTS idx_skill_usage_skill ON skill_usage(skill_name);
        CREATE INDEX IF NOT EXISTS idx_skill_usage_date ON skill_usage(date);

        CREATE TABLE IF NOT EXISTS schema_version (
            version INTEGER NOT NULL,
            migrated_at TEXT NOT NULL DEFAULT (datetime('now'))
        );
    """)

    # Seed schema version if empty
    row = conn.execute("SELECT version FROM schema_version ORDER BY rowid DESC LIMIT 1").fetchone()
    if row is None:
        conn.execute("INSERT INTO schema_version (version) VALUES (1)")

    conn.commit()


def _check_schema_version(conn: sqlite3.Connection) -> None:
    """Reject connection if schema version doesn't match expected."""
    try:
        row = conn.execute(
            "SELECT version FROM schema_version ORDER BY rowid DESC LIMIT 1"
        ).fetchone()
    except sqlite3.OperationalError:
        # Table doesn't exist yet -- _init_db will create it
        return
    if row is not None and row[0] != _EXPECTED_SCHEMA_VERSION:
        raise RuntimeError(
            f"Schema version mismatch: DB has v{row[0]}, code expects v{_EXPECTED_SCHEMA_VERSION}. "
            f"Run migrations or rebuild the database."
        )


def _get_conn() -> sqlite3.Connection:
    _DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(_DB_PATH))
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA synchronous=NORMAL")
    _check_schema_version(conn)
    _init_db(conn)
    return conn


def _is_indexed(conn: sqlite3.Connection, path: str, mtime_ns: int) -> bool:
    row = conn.execute(
        "SELECT mtime_ns FROM indexed_files WHERE source_file = ?", (path,)
    ).fetchone()
    return row is not None and row[0] == mtime_ns


def _mark_indexed(conn: sqlite3.Connection, path: str, mtime_ns: int) -> None:
    now = datetime.now(timezone.utc).isoformat()
    conn.execute(
        "INSERT OR REPLACE INTO indexed_files (source_file, mtime_ns, indexed_at) VALUES (?, ?, ?)",
        (path, mtime_ns, now),
    )


# -- Ingest adapters -------------------------------------------------------


def _ingest_session(conn: sqlite3.Connection, jsonl_path: Path) -> int:
    """Ingest a Claude Code session JSONL file."""
    path_str = str(jsonl_path)
    mtime_ns = jsonl_path.stat().st_mtime_ns
    if _is_indexed(conn, path_str, mtime_ns):
        return 0

    # Remove old entries for this file if re-indexing
    conn.execute("DELETE FROM documents WHERE source_file = ?", (path_str,))

    count = 0
    now = datetime.now(timezone.utc).isoformat()
    project_name = jsonl_path.parent.name

    # Collect all user and assistant text messages into one document per session
    messages = []
    session_ts = None

    try:
        with open(jsonl_path, "r", encoding="utf-8", errors="replace") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    entry = json.loads(line)
                except json.JSONDecodeError:
                    continue

                msg = entry.get("message", {})
                role = msg.get("role", "")
                ts = entry.get("timestamp", "")

                if not session_ts and ts:
                    session_ts = ts

                if role not in ("user", "assistant"):
                    continue

                content = msg.get("content", "")
                if isinstance(content, list):
                    # Extract text blocks from content array
                    parts = []
                    for block in content:
                        if isinstance(block, dict):
                            if block.get("type") == "text":
                                parts.append(block.get("text", ""))
                            elif block.get("type") == "tool_result":
                                c = block.get("content", "")
                                if isinstance(c, str):
                                    parts.append(c)
                        elif isinstance(block, str):
                            parts.append(block)
                    content = "\n".join(parts)

                if isinstance(content, str) and content.strip():
                    messages.append(f"[{role}] {content.strip()}")
    except (OSError, PermissionError):
        return 0

    if messages:
        full_text = "\n\n".join(messages)
        # Truncate very long sessions to keep index manageable
        if len(full_text) > 100_000:
            full_text = full_text[:100_000] + "\n[...truncated...]"

        conn.execute(
            "INSERT INTO documents (source, source_file, timestamp, title, content, indexed_at) VALUES (?, ?, ?, ?, ?, ?)",
            ("session", path_str, session_ts, f"Session: {project_name}", full_text, now),
        )
        count = 1

    _mark_indexed(conn, path_str, mtime_ns)
    return count


def _ingest_markdown(
    conn: sqlite3.Connection, md_path: Path, source: str
) -> int:
    """Ingest a markdown file (signal, failure, decision, security event)."""
    path_str = str(md_path)
    mtime_ns = md_path.stat().st_mtime_ns
    if _is_indexed(conn, path_str, mtime_ns):
        return 0

    conn.execute("DELETE FROM documents WHERE source_file = ?", (path_str,))

    try:
        text = md_path.read_text(encoding="utf-8", errors="replace")
    except (OSError, PermissionError):
        return 0

    if not text.strip():
        return 0

    # Extract title from first heading or filename
    title = md_path.stem
    for line in text.split("\n"):
        if line.startswith("# "):
            title = line[2:].strip()
            break

    # Try to extract date from filename
    ts = None
    name = md_path.stem
    if len(name) >= 10 and name[4] == "-" and name[7] == "-":
        ts = name[:10] + "T00:00:00Z"

    now = datetime.now(timezone.utc).isoformat()
    conn.execute(
        "INSERT INTO documents (source, source_file, timestamp, title, content, indexed_at) VALUES (?, ?, ?, ?, ?, ?)",
        (source, path_str, ts, title, text, now),
    )
    _mark_indexed(conn, path_str, mtime_ns)
    return 1


def _ingest_heartbeat(conn: sqlite3.Connection, log_path: Path) -> int:
    """Ingest a heartbeat log file."""
    path_str = str(log_path)
    mtime_ns = log_path.stat().st_mtime_ns
    if _is_indexed(conn, path_str, mtime_ns):
        return 0

    conn.execute("DELETE FROM documents WHERE source_file = ?", (path_str,))

    try:
        text = log_path.read_text(encoding="utf-8", errors="replace")
    except (OSError, PermissionError):
        return 0

    if not text.strip():
        return 0

    ts = None
    name = log_path.stem
    # heartbeat_2026-03-27 -> 2026-03-27
    if "heartbeat_" in name:
        date_part = name.replace("heartbeat_", "")
        if len(date_part) >= 10:
            ts = date_part[:10] + "T00:00:00Z"

    now = datetime.now(timezone.utc).isoformat()
    conn.execute(
        "INSERT INTO documents (source, source_file, timestamp, title, content, indexed_at) VALUES (?, ?, ?, ?, ?, ?)",
        ("heartbeat", path_str, ts, f"Heartbeat: {log_path.name}", text, now),
    )
    _mark_indexed(conn, path_str, mtime_ns)
    return 1


# -- Commands --------------------------------------------------------------


def cmd_build(args: argparse.Namespace) -> None:
    """Full rebuild of the index."""
    conn = _get_conn()
    # Clear everything for full rebuild
    conn.execute("DELETE FROM documents")
    conn.execute("DELETE FROM indexed_files")
    conn.execute("INSERT INTO documents_fts(documents_fts) VALUES ('delete-all')")
    conn.commit()

    total = _do_index(conn)
    conn.execute("PRAGMA wal_checkpoint(TRUNCATE)")
    conn.close()
    print(f"Index built: {total} documents indexed")
    print(f"Database: {_DB_PATH}")


def cmd_update(args: argparse.Namespace) -> None:
    """Incremental update -- only new/modified files."""
    conn = _get_conn()
    total = _do_index(conn)
    conn.execute("PRAGMA wal_checkpoint(TRUNCATE)")
    conn.close()
    print(f"Index updated: {total} new documents indexed")


def _do_index(conn: sqlite3.Connection) -> int:
    total = 0

    # 1. Claude Code sessions
    if _CLAUDE_PROJECTS.exists():
        for project_dir in _CLAUDE_PROJECTS.iterdir():
            if not project_dir.is_dir():
                continue
            for jsonl in project_dir.glob("*.jsonl"):
                total += _ingest_session(conn, jsonl)
                if total % 50 == 0 and total > 0:
                    conn.commit()

    # 2. Learning signals
    if _SIGNALS_DIR.exists():
        for md in _SIGNALS_DIR.glob("*.md"):
            total += _ingest_markdown(conn, md, "signal")
        # Also check processed/
        processed = _SIGNALS_DIR / "processed"
        if processed.exists():
            for md in processed.glob("*.md"):
                total += _ingest_markdown(conn, md, "signal")

    # 3. Failures
    if _FAILURES_DIR.exists():
        for md in _FAILURES_DIR.glob("*.md"):
            total += _ingest_markdown(conn, md, "failure")

    # 4. Synthesis
    if _SYNTHESIS_DIR.exists():
        for md in _SYNTHESIS_DIR.glob("*.md"):
            total += _ingest_markdown(conn, md, "synthesis")

    # 5. Decisions
    if _DECISIONS_DIR.exists():
        for md in _DECISIONS_DIR.glob("*.md"):
            total += _ingest_markdown(conn, md, "decision")

    # 6. Security events
    if _SECURITY_DIR.exists():
        for md in _SECURITY_DIR.glob("*.md"):
            total += _ingest_markdown(conn, md, "security")

    # 7. Heartbeat logs
    if _HEARTBEAT_DIR.exists():
        for log in _HEARTBEAT_DIR.glob("heartbeat_*.log"):
            total += _ingest_heartbeat(conn, log)

    conn.commit()
    return total


def cmd_search(args: argparse.Namespace) -> None:
    """Search the index."""
    conn = _get_conn()
    query = " ".join(args.query)
    if not query.strip():
        print("Usage: jarvis_index.py search <query>")
        return

    source_filter = ""
    params: list = [query]
    if args.source:
        source_filter = "AND d.source = ?"
        params.append(args.source)

    limit = args.limit or 10

    rows = conn.execute(
        f"""
        SELECT d.source, d.title, d.timestamp, snippet(documents_fts, 1, '>>>', '<<<', '...', 40) as snip,
               d.source_file
        FROM documents_fts fts
        JOIN documents d ON d.id = fts.rowid
        WHERE documents_fts MATCH ?
        {source_filter}
        ORDER BY rank
        LIMIT {limit}
        """,
        params,
    ).fetchall()

    if not rows:
        _safe_print(f"No results for: {query}")
        return

    _safe_print(f"Found {len(rows)} result(s) for: {query}\n")
    for i, (source, title, ts, snippet, source_file) in enumerate(rows, 1):
        date_str = ts[:10] if ts else "unknown"
        _safe_print(f"  {i}. [{source}] {title}")
        _safe_print(f"     Date: {date_str}")
        _safe_print(f"     {snippet}")
        _safe_print("")

    conn.close()


# -- Manifest backfill -----------------------------------------------------


def _parse_signal_frontmatter(md_path: Path) -> dict | None:
    """Extract structured metadata from a signal markdown file."""
    try:
        text = md_path.read_text(encoding="utf-8", errors="replace")
    except (OSError, PermissionError):
        return None

    meta: dict = {"filename": "", "title": "", "date": "", "source": "manual",
                  "category": "", "rating": None, "processed": 0}

    for line in text.split("\n"):
        line = line.strip()
        if line.startswith("# Signal:") or line.startswith("# signal:"):
            meta["title"] = line.split(":", 1)[1].strip()
        elif line.startswith("- Date:") or line.startswith("- date:"):
            meta["date"] = line.split(":", 1)[1].strip()
        elif line.startswith("- Rating:") or line.startswith("- rating:"):
            try:
                meta["rating"] = int(line.split(":", 1)[1].strip())
            except ValueError:
                pass
        elif line.startswith("- Category:") or line.startswith("- category:"):
            meta["category"] = line.split(":", 1)[1].strip()
        elif line.startswith("- Source:") or line.startswith("- source:"):
            meta["source"] = line.split(":", 1)[1].strip()

    if not meta["date"]:
        # Try extracting date from filename: 2026-03-25_title.md
        name = md_path.stem
        if len(name) >= 10 and name[4] == "-" and name[7] == "-":
            meta["date"] = name[:10]

    if not meta["date"]:
        return None

    return meta


def _backfill_signals(conn: sqlite3.Connection) -> int:
    """Backfill signals table from signal markdown files."""
    count = 0
    dirs = []
    if _SIGNALS_DIR.exists():
        dirs.append((_SIGNALS_DIR, False))
    processed = _SIGNALS_DIR / "processed"
    if processed.exists():
        dirs.append((processed, True))

    for dir_path, is_processed in dirs:
        for md in sorted(dir_path.glob("*.md")):
            meta = _parse_signal_frontmatter(md)
            if meta is None:
                continue
            rel = md.relative_to(_REPO_ROOT).as_posix()
            meta["filename"] = rel
            meta["processed"] = 1 if is_processed else 0
            before = conn.total_changes
            try:
                conn.execute(
                    """INSERT OR IGNORE INTO signals
                       (filename, title, date, source, category, rating, processed)
                       VALUES (?, ?, ?, ?, ?, ?, ?)""",
                    (rel, meta["title"], meta["date"], meta["source"],
                     meta["category"], meta["rating"], meta["processed"]),
                )
                if conn.total_changes > before:
                    count += 1
            except sqlite3.IntegrityError:
                pass

    conn.commit()
    return count


def _backfill_lineage(conn: sqlite3.Connection) -> int:
    """Backfill lineage table from signal_lineage.jsonl and synthesis docs."""
    count = 0
    lineage_file = _REPO_ROOT / "data" / "signal_lineage.jsonl"

    # Source 1: signal_lineage.jsonl (canonical)
    if lineage_file.exists():
        try:
            with open(lineage_file, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        entry = json.loads(line)
                    except json.JSONDecodeError:
                        continue
                    sig = entry.get("signal_filename", "")
                    syn = entry.get("synthesis_filename", "")
                    date = entry.get("date", "")
                    if sig and syn and date:
                        before = conn.total_changes
                        try:
                            conn.execute(
                                """INSERT OR IGNORE INTO lineage
                                   (signal_filename, synthesis_filename, date) VALUES (?, ?, ?)""",
                                (sig, syn, date),
                            )
                            if conn.total_changes > before:
                                count += 1
                        except sqlite3.IntegrityError:
                            pass
        except (OSError, PermissionError):
            pass

    # Source 2: parse synthesis docs for signal backreferences
    if _SYNTHESIS_DIR.exists():
        sig_ref_re = _re.compile(r"`(\d{4}-\d{2}-\d{2}_[a-zA-Z0-9_-]+)`")
        for syn_md in sorted(_SYNTHESIS_DIR.glob("*_synthesis*.md")):
            syn_name = syn_md.name
            # Extract date from synthesis filename
            syn_date = ""
            if len(syn_name) >= 10 and syn_name[4] == "-" and syn_name[7] == "-":
                syn_date = syn_name[:10]
            if not syn_date:
                continue

            try:
                text = syn_md.read_text(encoding="utf-8", errors="replace")
            except (OSError, PermissionError):
                continue

            for match in sig_ref_re.finditer(text):
                sig_stem = match.group(1)
                # Resolve to actual filename in signals/processed/
                sig_rel = f"memory/learning/signals/processed/{sig_stem}.md"
                sig_path = _REPO_ROOT / sig_rel
                if not sig_path.exists():
                    sig_rel = f"memory/learning/signals/{sig_stem}.md"
                    sig_path = _REPO_ROOT / sig_rel
                    if not sig_path.exists():
                        continue
                before = conn.total_changes
                try:
                    conn.execute(
                        """INSERT OR IGNORE INTO lineage
                           (signal_filename, synthesis_filename, date) VALUES (?, ?, ?)""",
                        (sig_rel, syn_name, syn_date),
                    )
                    if conn.total_changes > before:
                        count += 1
                except sqlite3.IntegrityError:
                    pass

    conn.commit()

    # Also write back to signal_lineage.jsonl for canonical persistence
    if not lineage_file.exists() or lineage_file.stat().st_size == 0:
        rows = conn.execute("SELECT signal_filename, synthesis_filename, date FROM lineage").fetchall()
        if rows:
            with open(lineage_file, "w", encoding="utf-8") as f:
                for sig, syn, date in rows:
                    f.write(json.dumps({"signal_filename": sig, "synthesis_filename": syn, "date": date}) + "\n")

    return count


_LOG_TS_RE = _re.compile(r"\[(\d{4}-\d{2}-\d{2})\s+(\d+:\d{2}:\d{2}\.\d+)\]")
_EXIT_CODE_RE = _re.compile(r"exit code:\s*(\d+)")
_PRODUCER_MAP = {
    "heartbeat": "Heartbeat run",
    "overnight": "Overnight self-improvement",
    "autoresearch": "TELOS introspection",
    "morning_feed": "Morning feed",
    "security_audit": "security audit",
    "steering_audit": "steering audit",
    "dispatcher": "autonomous dispatcher",
    "tasklist_stale": "tasklist stale",
}


def _parse_producer_from_logname(name: str) -> str | None:
    """Extract producer name from log filename like heartbeat_2026-03-29."""
    for prefix in _PRODUCER_MAP:
        if name.startswith(prefix + "_"):
            return prefix
    return None


def _backfill_producer_runs(conn: sqlite3.Connection) -> int:
    """Backfill producer_runs from data/logs/*.log."""
    count = 0
    if not _HEARTBEAT_DIR.exists():
        return 0

    for log_path in sorted(_HEARTBEAT_DIR.glob("*.log")):
        producer = _parse_producer_from_logname(log_path.stem)
        if producer is None:
            continue

        try:
            text = log_path.read_text(encoding="utf-8", errors="replace")
        except (OSError, PermissionError):
            continue

        lines = text.split("\n")
        started_at = None
        completed_at = None
        exit_code = None

        for line in lines:
            ts_match = _LOG_TS_RE.search(line)
            if ts_match:
                date_part = ts_match.group(1)
                time_part = ts_match.group(2)
                iso_ts = f"{date_part}T{time_part}"
                if started_at is None:
                    started_at = iso_ts
                completed_at = iso_ts

            ec_match = _EXIT_CODE_RE.search(line)
            if ec_match:
                exit_code = int(ec_match.group(1))

        if started_at is None:
            continue

        # Extract run_date from filename
        date_match = _re.search(r"(\d{4}-\d{2}-\d{2})", log_path.stem)
        run_date = date_match.group(1) if date_match else started_at[:10]

        # Compute duration
        duration = None
        if started_at and completed_at and started_at != completed_at:
            try:
                t1 = datetime.fromisoformat(started_at)
                t2 = datetime.fromisoformat(completed_at)
                duration = (t2 - t1).total_seconds()
            except ValueError:
                pass

        status = "success" if exit_code == 0 else ("failure" if exit_code else "unknown")
        rel_log = log_path.relative_to(_REPO_ROOT).as_posix()

        try:
            conn.execute(
                """INSERT OR IGNORE INTO producer_runs
                   (producer, run_date, started_at, completed_at, duration_seconds,
                    status, exit_code, log_path)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                (producer, run_date, started_at, completed_at, duration,
                 status, exit_code, rel_log),
            )
            count += 1
        except sqlite3.IntegrityError:
            pass

    conn.commit()
    return count


def cmd_backfill(args: argparse.Namespace) -> None:
    """Backfill all manifest tables from source files."""
    conn = _get_conn()

    _safe_print("Backfilling manifest tables...")

    sig_count = _backfill_signals(conn)
    sig_total = conn.execute("SELECT COUNT(*) FROM signals").fetchone()[0]
    _safe_print(f"  signals: {sig_total} rows (backfilled {sig_count})")

    lin_count = _backfill_lineage(conn)
    lin_total = conn.execute("SELECT COUNT(*) FROM lineage").fetchone()[0]
    _safe_print(f"  lineage: {lin_total} rows (backfilled {lin_count})")

    _backfill_producer_runs(conn)
    prod_total = conn.execute("SELECT COUNT(*) FROM producer_runs").fetchone()[0]
    producers = conn.execute("SELECT DISTINCT producer FROM producer_runs").fetchall()
    _safe_print(f"  producer_runs: {prod_total} rows ({len(producers)} producers)")

    ver = conn.execute("SELECT version FROM schema_version ORDER BY rowid DESC LIMIT 1").fetchone()
    _safe_print(f"  schema_version: v{ver[0] if ver else '?'}")

    conn.execute("PRAGMA wal_checkpoint(TRUNCATE)")
    conn.close()
    _safe_print("Backfill complete.")


def cmd_stats(args: argparse.Namespace) -> None:
    """Show index statistics."""
    conn = _get_conn()

    total = conn.execute("SELECT COUNT(*) FROM documents").fetchone()[0]
    print(f"Total documents: {total}")
    print()

    rows = conn.execute(
        "SELECT source, COUNT(*) as cnt FROM documents GROUP BY source ORDER BY cnt DESC"
    ).fetchall()
    for source, cnt in rows:
        print(f"  {source:12s} {cnt:>5d}")

    # Manifest tables
    manifest_tables = ["signals", "lineage", "producer_runs", "session_costs", "skill_usage"]
    print("\nManifest tables:")
    for tbl in manifest_tables:
        try:
            cnt = conn.execute(f"SELECT COUNT(*) FROM {tbl}").fetchone()[0]
            print(f"  {tbl:16s} {cnt:>5d}")
        except sqlite3.OperationalError:
            print(f"  {tbl:16s}   N/A")

    try:
        ver = conn.execute("SELECT version FROM schema_version ORDER BY rowid DESC LIMIT 1").fetchone()
        print(f"\nSchema version: {ver[0] if ver else 'none'}")
    except sqlite3.OperationalError:
        pass

    # DB file size
    if _DB_PATH.exists():
        size_mb = _DB_PATH.stat().st_size / (1024 * 1024)
        print(f"Database size: {size_mb:.1f} MB")

    conn.close()


# -- CLI -------------------------------------------------------------------


def _safe_print(text: str) -> None:
    """Print with ASCII fallback for Windows cp1252."""
    try:
        print(text)
    except UnicodeEncodeError:
        print(text.encode("ascii", errors="replace").decode("ascii"))


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Jarvis Knowledge Index -- unified search across all Jarvis data"
    )
    sub = parser.add_subparsers(dest="command")

    sub.add_parser("build", help="Full rebuild of the index")
    sub.add_parser("update", help="Incremental update (new/modified files only)")

    sp_search = sub.add_parser("search", help="Search the index")
    sp_search.add_argument("query", nargs="+", help="Search query")
    sp_search.add_argument("--source", help="Filter by source (session, signal, failure, decision, security, heartbeat)")
    sp_search.add_argument("--limit", type=int, default=10, help="Max results (default: 10)")

    sub.add_parser("stats", help="Show index statistics")
    sub.add_parser("backfill", help="Backfill manifest tables from source files")

    args = parser.parse_args()

    if args.command == "build":
        cmd_build(args)
    elif args.command == "update":
        cmd_update(args)
    elif args.command == "search":
        cmd_search(args)
    elif args.command == "stats":
        cmd_stats(args)
    elif args.command == "backfill":
        cmd_backfill(args)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
