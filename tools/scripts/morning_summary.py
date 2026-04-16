#!/usr/bin/env python3
"""Morning summary -- collects overnight autonomous work for Eric's review.

Runs at ~10am via Task Scheduler (after overnight 4am, autoresearch 7am,
morning feed 9am).

Behavior:
- If /vitals was already run today (data/vitals_latest.json collected_at = today):
  post a one-line ack to #epdev and exit -- no duplicate noise.
- Otherwise: post full summary to #jarvis-decisions so overnight work surfaces
  even if Eric never opened Claude Code.

Usage:
    python tools/scripts/morning_summary.py           # normal run
    python tools/scripts/morning_summary.py --dry-run  # print only, no Slack
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT))

VITALS_FILE = REPO_ROOT / "data" / "vitals_latest.json"


def vitals_ran_today() -> bool:
    """Return True if vitals_collector wrote vitals_latest.json today (UTC)."""
    if not VITALS_FILE.exists():
        return False
    try:
        data = json.loads(VITALS_FILE.read_text(encoding="utf-8"))
        collected_at = data.get("collected_at", "")
        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        return collected_at.startswith(today)
    except (json.JSONDecodeError, OSError):
        return False

BACKLOG_FILE = REPO_ROOT / "orchestration" / "task_backlog.jsonl"
DISPATCHER_RUNS = REPO_ROOT / "data" / "dispatcher_runs"
OVERNIGHT_DIR = REPO_ROOT / "memory" / "work" / "jarvis" / "autoresearch"


def get_unmerged_branches() -> list[dict]:
    """Get all jarvis/* branches not yet merged into main."""
    result = subprocess.run(
        ["git", "branch", "--no-merged", "main", "--list", "jarvis/*"],
        capture_output=True, text=True, encoding="utf-8", cwd=str(REPO_ROOT),
    )
    branches = []
    for line in result.stdout.splitlines():
        name = line.strip().lstrip("* ")
        if not name:
            continue
        # Get last commit info
        log = subprocess.run(
            ["git", "log", "-1", "--format=%s|||%cr", name],
            capture_output=True, text=True, encoding="utf-8", cwd=str(REPO_ROOT),
        )
        parts = log.stdout.strip().split("|||") if log.returncode == 0 else ["", ""]
        # Get diff stat
        stat = subprocess.run(
            ["git", "diff", "--shortstat", f"main...{name}"],
            capture_output=True, text=True, encoding="utf-8", cwd=str(REPO_ROOT),
        )
        branches.append({
            "name": name,
            "message": parts[0] if len(parts) > 0 else "",
            "age": parts[1] if len(parts) > 1 else "",
            "stat": stat.stdout.strip() if stat.returncode == 0 else "",
        })
    return branches


def get_recent_dispatcher_results() -> list[dict]:
    """Get dispatcher run reports from the last 24 hours."""
    if not DISPATCHER_RUNS.is_dir():
        return []
    results = []
    cutoff = datetime.now(timezone.utc).timestamp() - 86400
    for f in sorted(DISPATCHER_RUNS.glob("*.json"), reverse=True):
        if f.stat().st_mtime < cutoff:
            break
        try:
            data = json.loads(f.read_text(encoding="utf-8"))
            results.append(data)
        except (json.JSONDecodeError, OSError):
            pass
    return results


def get_backlog_status() -> dict:
    """Summarize backlog state."""
    if not BACKLOG_FILE.exists():
        return {"total": 0, "pending": 0, "done": 0, "failed": 0}
    tasks = []
    for line in BACKLOG_FILE.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line:
            tasks.append(json.loads(line))
    status_counts = {}
    for t in tasks:
        s = t.get("status", "unknown")
        status_counts[s] = status_counts.get(s, 0) + 1
    return {
        "total": len(tasks),
        "pending": status_counts.get("pending", 0),
        "done": status_counts.get("done", 0),
        "failed": status_counts.get("failed", 0),
        "deferred": status_counts.get("deferred", 0),
    }


def get_overnight_summary() -> str:
    """Check if overnight runner produced output today."""
    today = datetime.now().strftime("%Y-%m-%d")
    overnight_dir = OVERNIGHT_DIR / f"overnight-{today}"
    if overnight_dir.is_dir():
        files = list(overnight_dir.glob("*.md"))
        return f"Overnight: {len(files)} artifact(s) in overnight-{today}/"
    return "Overnight: no run today"


def build_summary() -> str:
    """Build the morning summary message."""
    lines = ["Morning Summary"]
    lines.append("=" * 40)

    # Unmerged branches
    branches = get_unmerged_branches()
    if branches:
        lines.append(f"\nBranches ready to merge: {len(branches)}")
        for b in branches:
            lines.append(f"  {b['name']} ({b['age']})")
            if b["message"]:
                lines.append(f"    {b['message']}")
            if b["stat"]:
                lines.append(f"    {b['stat']}")
    else:
        lines.append("\nNo unmerged branches.")

    # Dispatcher results (last 24h)
    results = get_recent_dispatcher_results()
    if results:
        lines.append(f"\nDispatcher runs (24h): {len(results)}")
        for r in results:
            status = r.get("status", "unknown")
            task_id = r.get("task_id", "?")
            emoji = "PASS" if status == "done" else "FAIL"
            lines.append(f"  [{emoji}] {task_id}: {status}")
            if status != "done" and r.get("failure_reason"):
                lines.append(f"    Reason: {r['failure_reason'][:80]}")

    # Backlog status
    backlog = get_backlog_status()
    lines.append(f"\nBacklog: {backlog['pending']} pending, "
                 f"{backlog['done']} done, {backlog['failed']} failed"
                 f" ({backlog['total']} total)")

    # Overnight
    lines.append(f"\n{get_overnight_summary()}")

    # Merge instructions
    if branches:
        lines.append("\nTo merge all ready branches:")
        for b in branches:
            lines.append(f"  git merge {b['name']}")

    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description="Morning summary for Eric")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    # If /vitals already ran today, just ack and exit -- no duplicate noise
    if vitals_ran_today():
        msg = "Morning summary: /vitals already run today. Overnight work covered."
        if args.dry_run:
            print(msg)
            return 0
        try:
            from tools.scripts.slack_notify import notify
            notify(msg, severity="routine")
            print(msg)
        except Exception as exc:
            print(f"Slack post failed: {exc}", file=sys.stderr)
        return 0

    # /vitals not run yet -- post full summary as fallback
    summary = build_summary()
    summary += "\n\n> /vitals not run yet. Open Claude Code and run /vitals for the full brief."

    if args.dry_run:
        print(summary)
        return 0

    # Post to #jarvis-decisions (always gets through, no cap)
    try:
        from tools.scripts.slack_notify import notify
        notify(summary, severity="decision")
        print("Morning summary posted to #jarvis-decisions")
    except Exception as exc:
        print(f"Slack post failed: {exc}", file=sys.stderr)
        print(summary)

    return 0


if __name__ == "__main__":
    sys.exit(main())
