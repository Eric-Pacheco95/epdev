"""backlog_dashboard.py -- Jarvis backlog kanban dashboard.

Usage:
    python tools/scripts/backlog_dashboard.py              # terminal kanban
    python tools/scripts/backlog_dashboard.py --json       # JSON data contract
    python tools/scripts/backlog_dashboard.py --backlog /path/to/file.jsonl
"""

import argparse
import json
import os
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

# Default paths -- resolved relative to this script's repo root
_SCRIPT_DIR = Path(__file__).parent
_REPO_ROOT = _SCRIPT_DIR.parent.parent
_DEFAULT_BACKLOG = _REPO_ROOT / "orchestration" / "task_backlog.jsonl"
_DEFAULT_ARCHIVE = _REPO_ROOT / "data" / "task_archive.jsonl"
_DISPATCHER_RUNS_DIR = _REPO_ROOT / "data" / "dispatcher_runs"

ALL_STATUSES = ["pending", "claimed", "executing", "verifying", "done", "failed", "manual_review"]


def load_backlog(path):
    """Load tasks from a JSONL file. Returns list of dicts."""
    p = Path(path)
    if not p.exists():
        return []
    tasks = []
    with open(p, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                tasks.append(json.loads(line))
            except json.JSONDecodeError:
                pass
    return tasks


def count_archive(archive_path):
    """Count lines in archive file. Returns 0 if file does not exist."""
    p = Path(archive_path)
    if not p.exists():
        return 0
    count = 0
    with open(p, encoding="utf-8") as f:
        for line in f:
            if line.strip():
                count += 1
    return count


def parse_date(date_str):
    """Parse a date string (YYYY-MM-DD or ISO timestamp). Returns date or None."""
    if not date_str:
        return None
    # Try ISO timestamp first
    for fmt in ("%Y-%m-%dT%H:%M:%S", "%Y-%m-%dT%H:%M:%S.%f", "%Y-%m-%d"):
        try:
            return datetime.strptime(date_str[:len(fmt.replace("%", "XX").replace("X", "0"))], fmt).date()
        except ValueError:
            pass
    # Fallback: try splitting on T
    try:
        return datetime.strptime(date_str.split("T")[0], "%Y-%m-%d").date()
    except ValueError:
        return None


def get_14d_cutoff():
    """Return a date 14 days ago."""
    return (datetime.now() - timedelta(days=14)).date()


def load_execution_time(run_report_path):
    """Try to read elapsed_min from a dispatcher run report. Returns float or None."""
    if not run_report_path:
        return None
    # run_report may be a relative path string
    p = Path(run_report_path)
    if not p.is_absolute():
        p = _REPO_ROOT / p
    if not p.exists():
        return None
    try:
        with open(p, encoding="utf-8") as f:
            data = json.load(f)
        # Accept various field names
        for key in ("elapsed_min", "elapsed_minutes", "duration_min", "duration_minutes"):
            if key in data:
                return float(data[key])
        # Try elapsed_sec
        if "elapsed_sec" in data:
            return float(data["elapsed_sec"]) / 60.0
        if "elapsed_seconds" in data:
            return float(data["elapsed_seconds"]) / 60.0
    except Exception:
        pass
    return None


def bucket_tasks(tasks):
    """Partition tasks into status buckets. Returns dict of status -> list."""
    buckets = {s: [] for s in ALL_STATUSES}
    for t in tasks:
        status = t.get("status", "pending")
        if status not in buckets:
            # Unknown status -- treat as pending
            status = "pending"
        buckets[status].append(t)
    return buckets


def compute_stats(tasks):
    """Compute 14-day stats from task list."""
    cutoff = get_14d_cutoff()
    completed_14d = []
    failed_14d = []
    exec_times = []

    for t in tasks:
        status = t.get("status", "")
        completed_str = t.get("completed")
        completed_date = parse_date(completed_str)

        if status == "done" and completed_date and completed_date >= cutoff:
            completed_14d.append(t)
            elapsed = load_execution_time(t.get("run_report"))
            if elapsed is not None:
                exec_times.append(elapsed)

        if status == "failed" and completed_date and completed_date >= cutoff:
            failed_14d.append(t)

    total = len(completed_14d) + len(failed_14d)
    success_rate = (len(completed_14d) / total) if total > 0 else 1.0

    avg_exec = None
    if exec_times:
        avg_exec = round(sum(exec_times) / len(exec_times), 1)

    pending_count = sum(1 for t in tasks if t.get("status") == "pending")
    manual_review_count = sum(1 for t in tasks if t.get("status") == "manual_review")

    return {
        "success_rate_14d": round(success_rate, 3),
        "tasks_completed_14d": len(completed_14d),
        "tasks_failed_14d": len(failed_14d),
        "avg_execution_min": avg_exec,
        "pending_count": pending_count,
        "manual_review_count": manual_review_count,
    }


def build_json_output(tasks, archive_path):
    """Build the JSON data contract dict."""
    buckets = bucket_tasks(tasks)
    stats = compute_stats(tasks)
    archive_count = count_archive(archive_path)

    columns = {}

    # pending
    columns["pending"] = [
        {
            "id": t.get("id", ""),
            "description": t.get("description", ""),
            "tier": t.get("tier", 0),
            "priority": t.get("priority", 3),
            "created": t.get("created", ""),
        }
        for t in buckets["pending"]
    ]

    # claimed (same shape as pending)
    columns["claimed"] = [
        {
            "id": t.get("id", ""),
            "description": t.get("description", ""),
            "tier": t.get("tier", 0),
            "priority": t.get("priority", 3),
            "created": t.get("created", ""),
        }
        for t in buckets["claimed"]
    ]

    # executing
    columns["executing"] = [
        {
            "id": t.get("id", ""),
            "branch": t.get("branch", ""),
            "elapsed_min": None,  # live elapsed not available from static backlog
            "model": t.get("model", ""),
        }
        for t in buckets["executing"]
    ]

    # verifying (same shape as executing)
    columns["verifying"] = [
        {
            "id": t.get("id", ""),
            "branch": t.get("branch", ""),
            "elapsed_min": None,
            "model": t.get("model", ""),
        }
        for t in buckets["verifying"]
    ]

    # done
    columns["done"] = [
        {
            "id": t.get("id", ""),
            "completed": t.get("completed", ""),
            "branch": t.get("branch", ""),
            "tier": t.get("tier", 0),
        }
        for t in buckets["done"]
    ]

    # failed
    columns["failed"] = [
        {
            "id": t.get("id", ""),
            "failure_reason": t.get("failure_reason", ""),
            "retry_count": t.get("retry_count", 0),
        }
        for t in buckets["failed"]
    ]

    # manual_review
    columns["manual_review"] = [
        {
            "id": t.get("id", ""),
            "branch": t.get("branch", ""),
            "notes": t.get("notes", ""),
        }
        for t in buckets["manual_review"]
    ]

    return {
        "generated": datetime.now().strftime("%Y-%m-%dT%H:%M:%S"),
        "columns": columns,
        "stats": stats,
        "archive_count": archive_count,
    }


def render_terminal(tasks, archive_path):
    """Render ASCII kanban to stdout."""
    if not tasks:
        print("No tasks in backlog")
        return

    buckets = bucket_tasks(tasks)
    stats = compute_stats(tasks)
    archive_count = count_archive(archive_path)
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M")

    print("")
    print("=== JARVIS BACKLOG ===                              " + now_str)
    print("")

    # Build display columns -- 4 per row
    row1_statuses = ["pending", "executing", "done", "failed"]
    row2_statuses = ["claimed", "verifying", "manual_review"]

    def format_col_header(status, count):
        label = status.upper().replace("_", " ")
        return "{} ({})".format(label, count)

    def format_task_line(t, status):
        tid = t.get("id", "?")
        tier = t.get("tier", "?")
        priority = t.get("priority")

        if status in ("pending", "claimed"):
            if priority is not None:
                return "{} [T{},P{}]".format(tid, tier, priority)
            return "{} [T{}]".format(tid, tier)
        elif status == "done":
            completed = t.get("completed", "")
            date_short = completed[5:10] if completed and len(completed) >= 10 else ""
            return "{} [T{}] {}".format(tid, tier, date_short)
        elif status in ("executing", "verifying"):
            model = t.get("model", "")
            return "{} [T{}] {}".format(tid, tier, model)
        elif status == "failed":
            retries = t.get("retry_count", 0)
            return "{} [T{}] r={}".format(tid, tier, retries)
        elif status == "manual_review":
            branch = t.get("branch", "")
            return "{} [T{}] {}".format(tid, tier, branch or "no-branch")
        return "{} [T{}]".format(tid, tier)

    col_width = 19

    def pad(s, w):
        if len(s) >= w:
            return s[:w - 1] + " "
        return s + " " * (w - len(s))

    # Row 1: pending | executing | done | failed
    headers1 = [pad(format_col_header(s, len(buckets[s])), col_width) for s in row1_statuses]
    print("   ".join(headers1))
    print("   ".join(["-" * col_width] * len(row1_statuses)))

    max_rows_1 = max(len(buckets[s]) for s in row1_statuses) if row1_statuses else 0
    for i in range(max_rows_1):
        cells = []
        for s in row1_statuses:
            if i < len(buckets[s]):
                cells.append(pad(format_task_line(buckets[s][i], s), col_width))
            else:
                cells.append(" " * col_width)
        print("   ".join(cells))

    print("")

    # Row 2: claimed | verifying | manual_review + archive note
    headers2 = [pad(format_col_header(s, len(buckets[s])), col_width) for s in row2_statuses]
    headers2.append(pad("ARCHIVED ({})".format(archive_count), col_width))
    print("   ".join(headers2))
    print("   ".join(["-" * col_width] * len(headers2)))

    max_rows_2 = max(len(buckets[s]) for s in row2_statuses) if row2_statuses else 0
    for i in range(max_rows_2):
        cells = []
        for s in row2_statuses:
            if i < len(buckets[s]):
                cells.append(pad(format_task_line(buckets[s][i], s), col_width))
            else:
                cells.append(" " * col_width)
        cells.append(" " * col_width)
        print("   ".join(cells))

    print("")

    # Stats line
    sr_pct = int(stats["success_rate_14d"] * 100)
    avg_str = "{}min".format(stats["avg_execution_min"]) if stats["avg_execution_min"] is not None else "N/A"
    print(
        "Stats (14d): {} done | {} failed | {}% success | avg {}".format(
            stats["tasks_completed_14d"],
            stats["tasks_failed_14d"],
            sr_pct,
            avg_str,
        )
    )
    print("")


def main():
    parser = argparse.ArgumentParser(description="Jarvis backlog dashboard")
    parser.add_argument(
        "--json",
        action="store_true",
        help="Output JSON data contract instead of terminal kanban",
    )
    parser.add_argument(
        "--backlog",
        default=str(_DEFAULT_BACKLOG),
        help="Path to task_backlog.jsonl (default: orchestration/task_backlog.jsonl)",
    )
    parser.add_argument(
        "--archive",
        default=str(_DEFAULT_ARCHIVE),
        help="Path to task_archive.jsonl (default: data/task_archive.jsonl)",
    )
    args = parser.parse_args()

    tasks = load_backlog(args.backlog)

    if args.json:
        output = build_json_output(tasks, args.archive)
        print(json.dumps(output, indent=2))
    else:
        render_terminal(tasks, args.archive)


if __name__ == "__main__":
    main()
