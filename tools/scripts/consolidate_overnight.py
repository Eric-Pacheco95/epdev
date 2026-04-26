#!/usr/bin/env python3
"""Jarvis Overnight Consolidation -- merge all overnight branches into one review branch.

Runs after all overnight jobs complete (dispatcher, overnight_runner).
Finds jarvis/auto-* and jarvis/overnight-* branches with unmerged work,
merges them into a single jarvis/review-YYYY-MM-DD branch, and produces
a summary report.

Usage:
    python tools/scripts/consolidate_overnight.py              # normal run
    python tools/scripts/consolidate_overnight.py --dry-run    # list branches, no merge
    python tools/scripts/consolidate_overnight.py --test       # self-test

Outputs:
    jarvis/review-YYYY-MM-DD branch      -- consolidated review branch
    data/overnight_summary/YYYY-MM-DD.json  -- machine-readable summary
    data/overnight_summary/YYYY-MM-DD.md    -- human-readable morning report

Scheduling:
    Runs after dispatcher (e.g., 6am if dispatcher runs at 5am).
    Morning feed reads the summary at 9am.
"""

from __future__ import annotations

import json
import os
import re
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT))

from tools.scripts.lib.worktree import cleanup_old_branches

SUMMARY_DIR = REPO_ROOT / "data" / "overnight_summary"
RUNNER_WAIT_TIMEOUT_S = 900   # 15 min cap waiting for overnight runner to release claude lock
RUNNER_WAIT_POLL_S = 30

# Branch prefixes created by overnight jobs
OVERNIGHT_PREFIXES = [
    "jarvis/auto-",
    "jarvis/overnight-",
]


def get_main_branch() -> str:
    """Detect the default branch (main or master)."""
    for name in ("main", "master"):
        result = subprocess.run(
            ["git", "rev-parse", "--verify", name],
            capture_output=True, text=True, encoding="utf-8",
            cwd=str(REPO_ROOT),
        )
        if result.returncode == 0:
            return name
    return "main"


def find_overnight_branches() -> list[dict[str, Any]]:
    """Find all jarvis/* branches with commits not on main."""
    main = get_main_branch()
    branches = []

    result = subprocess.run(
        ["git", "branch", "--list", "jarvis/*"],
        capture_output=True, text=True, encoding="utf-8",
        cwd=str(REPO_ROOT),
    )

    for line in result.stdout.splitlines():
        name = line.strip().lstrip("* ")
        if not name:
            continue

        # Only include branches matching overnight prefixes
        is_overnight = any(name.startswith(p) for p in OVERNIGHT_PREFIXES)
        if not is_overnight:
            continue

        # Check if branch has commits ahead of main
        ahead_result = subprocess.run(
            ["git", "rev-list", "--count", f"{main}..{name}"],
            capture_output=True, text=True, encoding="utf-8",
            cwd=str(REPO_ROOT),
        )
        if ahead_result.returncode != 0:
            continue

        ahead_count = int(ahead_result.stdout.strip() or "0")
        if ahead_count == 0:
            continue

        # Get last commit info
        log_result = subprocess.run(
            ["git", "log", "-1", "--format=%ct|%s", name],
            capture_output=True, text=True, encoding="utf-8",
            cwd=str(REPO_ROOT),
        )
        commit_ts = 0
        commit_msg = ""
        if log_result.returncode == 0 and "|" in log_result.stdout:
            parts = log_result.stdout.strip().split("|", 1)
            try:
                commit_ts = int(parts[0])
            except ValueError:
                pass
            commit_msg = parts[1] if len(parts) > 1 else ""

        # Get diff stat vs main
        diff_result = subprocess.run(
            ["git", "diff", "--stat", f"{main}...{name}"],
            capture_output=True, text=True, encoding="utf-8",
            cwd=str(REPO_ROOT),
        )
        diff_stat = diff_result.stdout.strip() if diff_result.returncode == 0 else ""

        # Get file list
        files_result = subprocess.run(
            ["git", "diff", "--name-only", f"{main}...{name}"],
            capture_output=True, text=True, encoding="utf-8",
            cwd=str(REPO_ROOT),
        )
        files_changed = files_result.stdout.strip().splitlines() if files_result.returncode == 0 else []

        branches.append({
            "name": name,
            "ahead": ahead_count,
            "commit_ts": commit_ts,
            "commit_msg": commit_msg,
            "diff_stat": diff_stat,
            "files_changed": files_changed,
        })

    # Sort by commit timestamp (oldest first for merge order)
    branches.sort(key=lambda b: b["commit_ts"])
    return branches


def get_dispatcher_reports(today: str) -> list[dict]:
    """Read dispatcher run reports from today."""
    runs_dir = REPO_ROOT / "data" / "dispatcher_runs"
    if not runs_dir.is_dir():
        return []

    reports = []
    for f in runs_dir.glob(f"*_{today.replace('-', '')}*.json"):
        try:
            report = json.loads(f.read_text(encoding="utf-8"))
            reports.append(report)
        except (json.JSONDecodeError, OSError):
            pass

    return reports


def create_review_branch(branches: list[dict], today: str) -> dict[str, Any]:
    """Merge all overnight branches into jarvis/review-YYYY-MM-DD.

    Uses octopus merge when possible (no conflicts), falls back to
    sequential merge-or-cherry-pick for each branch.

    Returns a result dict with status and details.
    """
    main = get_main_branch()
    review_branch = f"jarvis/review-{today}"

    result = {
        "review_branch": review_branch,
        "merged": [],
        "conflicts": [],
        "skipped": [],
    }

    # Delete old review branch if it exists (re-run scenario)
    subprocess.run(
        ["git", "branch", "-D", review_branch],
        capture_output=True, text=True, encoding="utf-8",
        cwd=str(REPO_ROOT),
    )

    # Create review branch from main
    create_result = subprocess.run(
        ["git", "branch", review_branch, main],
        capture_output=True, text=True, encoding="utf-8",
        cwd=str(REPO_ROOT),
    )
    if create_result.returncode != 0:
        result["error"] = f"Failed to create {review_branch}: {create_result.stderr.strip()}"
        return result

    # Merge each branch sequentially (safer than octopus on Windows)
    for branch_info in branches:
        name = branch_info["name"]

        # Check for file conflicts before merging (tree-level check)
        merge_result = subprocess.run(
            ["git", "merge-tree", "--write-tree", review_branch, name],
            capture_output=True, text=True, encoding="utf-8",
            cwd=str(REPO_ROOT),
        )

        # git merge-tree exits 0 on clean merge, 1 on conflict
        if merge_result.returncode != 0:
            # Try a test merge to see if it's a real conflict
            # Use a temporary branch approach
            result["conflicts"].append({
                "branch": name,
                "reason": "merge conflict detected",
                "files": branch_info["files_changed"][:5],
            })
            continue

        # Perform actual merge using plumbing (no checkout needed)
        # We use git merge with a temporary checkout approach
        merge_exec = subprocess.run(
            ["git", "checkout", review_branch],
            capture_output=True, text=True, encoding="utf-8",
            cwd=str(REPO_ROOT),
        )
        if merge_exec.returncode != 0:
            result["skipped"].append({
                "branch": name,
                "reason": f"checkout failed: {merge_exec.stderr.strip()[:100]}",
            })
            continue

        merge_exec = subprocess.run(
            ["git", "merge", "--no-edit", name,
             "-m", f"consolidate: merge {name} into review"],
            capture_output=True, text=True, encoding="utf-8",
            cwd=str(REPO_ROOT),
        )

        if merge_exec.returncode == 0:
            result["merged"].append({
                "branch": name,
                "commits": branch_info["ahead"],
                "files": branch_info["files_changed"],
            })
        else:
            # Abort failed merge
            subprocess.run(
                ["git", "merge", "--abort"],
                capture_output=True, text=True, encoding="utf-8",
                cwd=str(REPO_ROOT),
            )
            result["conflicts"].append({
                "branch": name,
                "reason": merge_exec.stderr.strip()[:200],
                "files": branch_info["files_changed"][:5],
            })

    # Return to the original branch
    current_branch = subprocess.run(
        ["git", "rev-parse", "--abbrev-ref", "HEAD"],
        capture_output=True, text=True, encoding="utf-8",
        cwd=str(REPO_ROOT),
    )
    if current_branch.stdout.strip() == review_branch:
        subprocess.run(
            ["git", "checkout", "-"],
            capture_output=True, text=True, encoding="utf-8",
            cwd=str(REPO_ROOT),
        )

    return result


def generate_summary_md(
    branches: list[dict],
    merge_result: dict,
    dispatcher_reports: list[dict],
    today: str,
) -> str:
    """Generate human-readable overnight summary."""
    lines = [
        f"# Overnight Summary -- {today}",
        "",
    ]

    # Review branch status
    review_branch = merge_result.get("review_branch", "N/A")
    merged_count = len(merge_result.get("merged", []))
    conflict_count = len(merge_result.get("conflicts", []))
    total = len(branches)

    if merged_count == total and total > 0:
        lines.append(f"Review branch: `{review_branch}` -- {merged_count} branches merged cleanly")
    elif total == 0:
        lines.append("No overnight branches with new work. Idle Is Success.")
    else:
        lines.append(f"Review branch: `{review_branch}` -- {merged_count}/{total} merged, {conflict_count} conflicts")

    lines.append("")

    # Dispatcher results
    if dispatcher_reports:
        lines.append("## Dispatcher Tasks")
        lines.append("")
        for report in dispatcher_reports:
            task_id = report.get("task_id", "?")
            status = report.get("status", "?")
            model = report.get("model", "?")
            isc_passed = report.get("isc_passed", "?")
            isc_total = report.get("isc_total", "?")
            diff = report.get("diff_stat", "N/A")

            status_mark = "[DONE]" if status == "done" else "[FAIL]"
            lines.append(f"- {status_mark} `{task_id}` (model: {model}, ISC: {isc_passed}/{isc_total})")

            if status != "done":
                reason = report.get("failure_reason", "unknown")
                lines.append(f"  Reason: {reason}")

            # Show first 3 lines of diff stat
            if diff and diff != "N/A":
                for diff_line in diff.splitlines()[:3]:
                    lines.append(f"  {diff_line}")

        lines.append("")

    # Merged branches detail
    if merge_result.get("merged"):
        lines.append("## Merged Branches")
        lines.append("")
        for m in merge_result["merged"]:
            lines.append(f"- `{m['branch']}` ({m['commits']} commits, {len(m['files'])} files)")
            for f in m["files"][:5]:
                lines.append(f"  - {f}")
            if len(m["files"]) > 5:
                lines.append(f"  - ... and {len(m['files']) - 5} more")
        lines.append("")

    # Conflicts
    if merge_result.get("conflicts"):
        lines.append("## Conflicts (need manual review)")
        lines.append("")
        for c in merge_result["conflicts"]:
            lines.append(f"- `{c['branch']}`: {c['reason']}")
            for f in c.get("files", []):
                lines.append(f"  - {f}")
        lines.append("")

    # Cleanup info
    lines.append("## Next Steps")
    lines.append("")
    if merged_count > 0:
        lines.append(f"1. Review: `git log --oneline {review_branch}`")
        lines.append(f"2. Diff: `git diff main...{review_branch}`")
        lines.append(f"3. Merge: `git merge {review_branch}` (from your feature branch)")
    if conflict_count > 0:
        lines.append(f"4. Resolve conflicts manually for {conflict_count} branch(es)")
    if total == 0:
        lines.append("Nothing to review -- all quiet overnight.")

    return "\n".join(lines)


def save_summary(
    branches: list[dict],
    merge_result: dict,
    dispatcher_reports: list[dict],
    today: str,
) -> tuple[Path, Path]:
    """Save both JSON and MD summaries."""
    SUMMARY_DIR.mkdir(parents=True, exist_ok=True)

    # JSON summary (machine-readable)
    json_path = SUMMARY_DIR / f"{today}.json"
    summary_data = {
        "date": today,
        "generated": datetime.now().isoformat(),
        "branches_found": len(branches),
        "branches_merged": len(merge_result.get("merged", [])),
        "branches_conflicted": len(merge_result.get("conflicts", [])),
        "review_branch": merge_result.get("review_branch"),
        "dispatcher_reports": [
            {
                "task_id": r.get("task_id"),
                "status": r.get("status"),
                "isc_passed": r.get("isc_passed"),
                "isc_total": r.get("isc_total"),
            }
            for r in dispatcher_reports
        ],
        "merge_result": merge_result,
    }
    json_path.write_text(
        json.dumps(summary_data, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )

    # MD summary (human-readable, also consumed by morning feed)
    md_path = SUMMARY_DIR / f"{today}.md"
    md_content = generate_summary_md(branches, merge_result, dispatcher_reports, today)
    md_path.write_text(md_content, encoding="utf-8")

    return json_path, md_path


def _active_lock_slots() -> list[Path]:
    """Return all currently-existing claude_session.*.lock files under data/."""
    import glob as _glob
    pattern = str(REPO_ROOT / "data" / "claude_session.*.lock")
    return [Path(p) for p in _glob.glob(pattern)]


def wait_for_claude_lock(timeout_s: int = RUNNER_WAIT_TIMEOUT_S,
                         poll_s: int = RUNNER_WAIT_POLL_S) -> tuple[bool, str]:
    """Wait for all data/claude_session.*.lock slots to be free before consolidating.

    Overnight runner can run up to 2 hours starting at 04:00 EDT (08:00 UTC),
    finishing as late as 10:00 UTC. Consolidate is scheduled at 10:30 UTC --
    a 30-min margin with no defense in depth. This poll closes that gap by
    deferring consolidation up to `timeout_s` seconds while any slot is held.

    Returns (proceeded, reason). proceeded=True means all slots are free or
    none were present; False means the timeout elapsed and the caller should skip.
    """
    import time

    slots = _active_lock_slots()
    if not slots:
        return True, "no lock present"

    waited = 0
    while waited < timeout_s:
        slots = _active_lock_slots()
        if not slots:
            return True, f"lock released after {waited}s"
        owners = []
        for slot_path in slots:
            try:
                data = json.loads(slot_path.read_text(encoding="utf-8"))
                owners.append(data.get("owner", "?"))
            except (json.JSONDecodeError, OSError):
                owners.append("?")
        print(f"  claude lock held by {owners}; waited {waited}s/{timeout_s}s")
        time.sleep(poll_s)
        waited += poll_s

    return False, f"lock still held after {timeout_s}s"


def consolidate(dry_run: bool = False, no_wait: bool = False) -> int:
    """Main consolidation flow."""
    today = datetime.now().strftime("%Y-%m-%d")
    print(f"\n=== Jarvis Overnight Consolidation === {today}")

    # 0. Wait for any in-flight claude -p run (overnight runner, dispatcher,
    #    autoresearch) to release its lock before consolidating. Prevents
    #    grabbing branches mid-flight when overnight runner overruns.
    if not dry_run and not no_wait:
        proceeded, reason = wait_for_claude_lock()
        if not proceeded:
            print(f"  ABORT: {reason}. Re-run consolidate later.", file=sys.stderr)
            return 2
        print(f"  claude lock check: {reason}")

    # 1. Find overnight branches
    branches = find_overnight_branches()
    print(f"  Found {len(branches)} overnight branch(es) with new work")

    for b in branches:
        # Sanitize commit message for Windows cp1252 terminal
        safe_msg = b['commit_msg'][:60].encode("ascii", errors="replace").decode("ascii")
        print(f"    {b['name']}: {b['ahead']} commits ahead -- {safe_msg}")

    # 2. Read dispatcher reports
    dispatcher_reports = get_dispatcher_reports(today)
    print(f"  Dispatcher reports: {len(dispatcher_reports)}")

    if dry_run:
        print("\n[DRY RUN] Would create review branch and merge. No changes made.")
        # Still save the summary so morning feed can read it
        if branches or dispatcher_reports:
            merge_result = {
                "review_branch": f"jarvis/review-{today}",
                "merged": [],
                "conflicts": [],
                "skipped": [],
            }
            _, md_path = save_summary(branches, merge_result, dispatcher_reports, today)
            print(f"  Summary (dry run): {md_path}")
        return 0

    # 3. Create consolidated review branch
    if branches:
        merge_result = create_review_branch(branches, today)
        merged = len(merge_result.get("merged", []))
        conflicts = len(merge_result.get("conflicts", []))
        print(f"  Merged: {merged}/{len(branches)}, Conflicts: {conflicts}")

        if merge_result.get("error"):
            print(f"  ERROR: {merge_result['error']}", file=sys.stderr)
    else:
        merge_result = {
            "review_branch": f"jarvis/review-{today}",
            "merged": [],
            "conflicts": [],
            "skipped": [],
        }
        print("  No branches to merge. Idle Is Success.")

    # 4. Save summaries
    json_path, md_path = save_summary(branches, merge_result, dispatcher_reports, today)
    print(f"  JSON summary: {json_path}")
    print(f"  MD summary: {md_path}")

    # 5. Clean up old review branches (keep 7 days)
    cleanup_old_branches(prefix="jarvis/review-", days=7)
    # Clean up old auto branches (keep 14 days)
    cleanup_old_branches(prefix="jarvis/auto-", days=14)
    # Clean up old overnight branches (keep 7 days)
    cleanup_old_branches(prefix="jarvis/overnight-", days=7)

    # 6. Notify via Slack
    try:
        from tools.scripts.slack_notify import notify

        merged = len(merge_result.get("merged", []))
        conflicts = len(merge_result.get("conflicts", []))
        total = len(branches)
        tasks_done = sum(1 for r in dispatcher_reports if r.get("status") == "done")
        tasks_total = len(dispatcher_reports)

        if total == 0 and tasks_total == 0:
            # Idle Is Success -- don't spam Slack
            pass
        else:
            msg = (
                f"Overnight consolidation: {merged}/{total} branches merged"
                f"{f', {conflicts} conflicts' if conflicts else ''}"
            )
            if tasks_total:
                msg += f"\nDispatcher: {tasks_done}/{tasks_total} tasks done"
            if merged > 0:
                msg += f"\nReview: git log --oneline {merge_result['review_branch']}"

            notify(msg, severity="routine")
    except Exception as exc:
        print(f"  WARNING: Slack notify failed: {exc}", file=sys.stderr)

    print("\nConsolidation complete.")
    return 0


# -- Self-test ---------------------------------------------------------------

def self_test() -> int:
    """Run self-tests."""
    print("=== Consolidation Self-Test ===\n")
    ok = True

    # Test 1: find_overnight_branches runs without error
    print("Test 1: find_overnight_branches...")
    try:
        branches = find_overnight_branches()
        print(f"  PASS: Found {len(branches)} branches")
    except Exception as exc:
        print(f"  FAIL: {exc}")
        ok = False

    # Test 2: get_dispatcher_reports runs without error
    print("Test 2: get_dispatcher_reports...")
    try:
        today = datetime.now().strftime("%Y-%m-%d")
        reports = get_dispatcher_reports(today)
        print(f"  PASS: Found {len(reports)} reports")
    except Exception as exc:
        print(f"  FAIL: {exc}")
        ok = False

    # Test 3: Summary generation works
    print("Test 3: generate_summary_md...")
    try:
        md = generate_summary_md(
            branches=[{"name": "test", "ahead": 1, "commit_ts": 0,
                       "commit_msg": "test", "diff_stat": "", "files_changed": ["a.py"]}],
            merge_result={"review_branch": "jarvis/review-test",
                         "merged": [{"branch": "test", "commits": 1, "files": ["a.py"]}],
                         "conflicts": [], "skipped": []},
            dispatcher_reports=[],
            today="2026-01-01",
        )
        assert "Overnight Summary" in md
        assert "jarvis/review-test" in md
        print("  PASS: Summary generated")
    except Exception as exc:
        print(f"  FAIL: {exc}")
        ok = False

    # Test 4: get_main_branch
    print("Test 4: get_main_branch...")
    try:
        main = get_main_branch()
        assert main in ("main", "master")
        print(f"  PASS: main branch = {main}")
    except Exception as exc:
        print(f"  FAIL: {exc}")
        ok = False

    # Test 5: wait_for_claude_lock returns immediately when no lock present
    print("Test 5: wait_for_claude_lock (no lock)...")
    try:
        # Note: this only runs if there is no lock; otherwise just checks the
        # function exists and is callable with a 0-timeout to avoid blocking.
        proceeded, reason = wait_for_claude_lock(timeout_s=0, poll_s=0)
        if not _active_lock_slots():
            assert proceeded, f"expected proceed=True with no lock, got reason={reason}"
            print(f"  PASS: no lock -> proceeded ({reason})")
        else:
            assert not proceeded, "expected proceed=False with held lock + 0 timeout"
            print(f"  PASS: lock held -> aborted ({reason})")
    except Exception as exc:
        print(f"  FAIL: {exc}")
        ok = False

    print(f"\n{'ALL TESTS PASSED' if ok else 'SOME TESTS FAILED'}")
    return 0 if ok else 1


def main() -> None:
    import argparse
    parser = argparse.ArgumentParser(description="Jarvis Overnight Consolidation")
    parser.add_argument("--dry-run", action="store_true", help="List branches, no merge")
    parser.add_argument("--test", action="store_true", help="Run self-test")
    parser.add_argument("--no-wait", action="store_true",
                        help="Skip claude slot-lock wait (manual ad-hoc runs)")
    args = parser.parse_args()

    if args.test:
        sys.exit(self_test())

    sys.exit(consolidate(dry_run=args.dry_run, no_wait=args.no_wait))


if __name__ == "__main__":
    main()
