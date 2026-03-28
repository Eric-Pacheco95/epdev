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
import os
import sqlite3
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

# -- Paths -----------------------------------------------------------------

_SCRIPT_DIR = Path(__file__).resolve().parent
_REPO_ROOT = _SCRIPT_DIR.parents[1]
_DB_PATH = _REPO_ROOT / "data" / "jarvis_index.db"

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
    conn.commit()


def _get_conn() -> sqlite3.Connection:
    _DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(_DB_PATH))
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA synchronous=NORMAL")
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
    conn.close()
    print(f"Index built: {total} documents indexed")
    print(f"Database: {_DB_PATH}")


def cmd_update(args: argparse.Namespace) -> None:
    """Incremental update -- only new/modified files."""
    conn = _get_conn()
    total = _do_index(conn)
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

    # DB file size
    if _DB_PATH.exists():
        size_mb = _DB_PATH.stat().st_size / (1024 * 1024)
        print(f"\nDatabase size: {size_mb:.1f} MB")

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

    args = parser.parse_args()

    if args.command == "build":
        cmd_build(args)
    elif args.command == "update":
        cmd_update(args)
    elif args.command == "search":
        cmd_search(args)
    elif args.command == "stats":
        cmd_stats(args)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
