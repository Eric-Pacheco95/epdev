#!/usr/bin/env python3
"""Branch lifecycle tracker for Jarvis autonomous branches.

Scans for stale jarvis/auto-* and jarvis/overnight-* branches that have
not been merged or discarded within a configurable TTL (default 7 days).

Usage:
    python tools/scripts/branch_lifecycle.py              # print report
    python tools/scripts/branch_lifecycle.py --json       # JSON output
    python tools/scripts/branch_lifecycle.py --notify     # print + Slack alert for stale branches
    python tools/scripts/branch_lifecycle.py --self-test  # run self-tests

Also exposes collect_stale_branches() for use as a heartbeat collector.
"""

from __future__ import annotations

import json
import os
import re
import subprocess
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
BRANCH_PREFIXES = ("jarvis/auto-", "jarvis/overnight-")
DEFAULT_TTL_DAYS = 7


# ---------------------------------------------------------------------------
# Core logic
# ---------------------------------------------------------------------------

def _git(*args: str, cwd: str | Path | None = None) -> str:
    """Run a git command and return stdout."""
    result = subprocess.run(
        ["git", *args],
        capture_output=True,
        text=True,
        encoding="utf-8",
        cwd=cwd or REPO_ROOT,
        timeout=30,
    )
    if result.returncode != 0:
        raise RuntimeError(f"git {' '.join(args)} failed: {result.stderr.strip()}")
    return result.stdout.strip()


def list_jarvis_branches() -> list[str]:
    """Return all local branches matching Jarvis autonomous prefixes."""
    raw = _git("branch", "--list", "--no-color")
    branches = []
    for line in raw.splitlines():
        name = line.strip().lstrip("* ")
        if any(name.startswith(p) for p in BRANCH_PREFIXES):
            branches.append(name)
    return branches


def branch_last_commit_date(branch: str) -> datetime:
    """Return the date of the most recent commit on a branch."""
    iso = _git("log", "-1", "--format=%aI", branch)
    return datetime.fromisoformat(iso)


def branch_is_merged(branch: str, target: str = "main") -> bool:
    """Check if branch is fully merged into target."""
    try:
        merged = _git("branch", "--merged", target, "--list", branch)
        return branch in merged
    except RuntimeError:
        return False


def branch_commit_count(branch: str, base: str = "main") -> int:
    """Count commits on branch not in base."""
    try:
        log = _git("log", "--oneline", f"{base}..{branch}")
        return len(log.splitlines()) if log else 0
    except RuntimeError:
        return 0


def branch_diff_stat(branch: str, base: str = "main") -> str:
    """Get short diffstat for branch vs base."""
    try:
        stat = _git("diff", "--stat", "--stat-width=60", f"{base}..{branch}")
        lines = stat.strip().splitlines()
        return lines[-1].strip() if lines else "no changes"
    except RuntimeError:
        return "unknown"


def scan_branches(ttl_days: int = DEFAULT_TTL_DAYS) -> list[dict]:
    """Scan all Jarvis branches and return status info for each.

    Returns list of dicts with:
        name, last_commit, age_days, is_merged, is_stale,
        commit_count, diff_summary
    """
    now = datetime.now(timezone.utc)
    cutoff = now - timedelta(days=ttl_days)
    branches = list_jarvis_branches()
    results = []

    for branch in branches:
        try:
            last_commit = branch_last_commit_date(branch)
            # Make timezone-aware if naive
            if last_commit.tzinfo is None:
                last_commit = last_commit.replace(tzinfo=timezone.utc)
            age_days = (now - last_commit).days
            merged = branch_is_merged(branch)
            commits = branch_commit_count(branch)
            diff = branch_diff_stat(branch)

            results.append({
                "name": branch,
                "last_commit": last_commit.isoformat(),
                "age_days": age_days,
                "is_merged": merged,
                "is_stale": last_commit < cutoff and not merged,
                "commit_count": commits,
                "diff_summary": diff,
            })
        except RuntimeError as exc:
            results.append({
                "name": branch,
                "error": str(exc),
                "is_stale": False,
            })

    return results


def format_report(branches: list[dict]) -> str:
    """Format branch scan results as a human-readable report."""
    if not branches:
        return "No Jarvis autonomous branches found."

    stale = [b for b in branches if b.get("is_stale")]
    merged = [b for b in branches if b.get("is_merged")]
    active = [b for b in branches if not b.get("is_stale") and not b.get("is_merged") and "error" not in b]

    lines = [f"Branch Lifecycle Report -- {datetime.now().strftime('%Y-%m-%d %H:%M')}"]
    lines.append(f"Total: {len(branches)} | Stale: {len(stale)} | Merged: {len(merged)} | Active: {len(active)}")
    lines.append("")

    if stale:
        lines.append("STALE (>7 days, not merged -- action required):")
        for b in sorted(stale, key=lambda x: x.get("age_days", 0), reverse=True):
            lines.append(f"  {b['name']} -- {b['age_days']}d old, {b['commit_count']} commits, {b['diff_summary']}")
        lines.append("")

    if merged:
        lines.append("MERGED (safe to delete):")
        for b in merged:
            lines.append(f"  {b['name']} -- merged, {b['age_days']}d old")
        lines.append("")

    if active:
        lines.append("ACTIVE (within TTL):")
        for b in active:
            lines.append(f"  {b['name']} -- {b['age_days']}d old, {b['commit_count']} commits")

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Heartbeat collector interface
# ---------------------------------------------------------------------------

def collect_stale_branches(cfg: dict, root_dir: Path, _prev: dict = None) -> dict:
    """Heartbeat collector: count stale Jarvis branches."""
    name = cfg.get("name", "stale_branches")
    ttl = cfg.get("ttl_days", DEFAULT_TTL_DAYS)

    try:
        branches = scan_branches(ttl_days=ttl)
        stale = [b for b in branches if b.get("is_stale")]
        merged = [b for b in branches if b.get("is_merged")]
        total = len(branches)

        stale_names = ", ".join(b["name"] for b in stale) if stale else "none"
        detail = "total=%d stale=%d merged=%d stale_branches=[%s]" % (
            total, len(stale), len(merged), stale_names
        )
        return {"name": name, "value": len(stale), "unit": "count", "detail": detail}
    except Exception as exc:
        return {"name": name, "value": None, "unit": "count",
                "detail": "stale_branches error: %s" % exc}


# ---------------------------------------------------------------------------
# Slack notification
# ---------------------------------------------------------------------------

def notify_stale(branches: list[dict]) -> None:
    """Send Slack alert for stale branches."""
    stale = [b for b in branches if b.get("is_stale")]
    if not stale:
        print("No stale branches -- skipping Slack notification.")
        return

    sys.path.insert(0, str(REPO_ROOT))
    from tools.scripts.slack_notify import notify

    lines = [f"*Branch Lifecycle Alert* -- {len(stale)} stale branch(es) need action:"]
    for b in sorted(stale, key=lambda x: x.get("age_days", 0), reverse=True):
        lines.append(f"  `{b['name']}` -- {b['age_days']}d old, {b['commit_count']} commits")
    lines.append("\nReview with: `git log --oneline main..<branch>`")
    lines.append("Merge: `git merge <branch>` | Discard: `git branch -D <branch>`")

    notify("\n".join(lines), severity="routine")
    print(f"Slack notification sent for {len(stale)} stale branches.")


# ---------------------------------------------------------------------------
# Self-test
# ---------------------------------------------------------------------------

def _self_test() -> None:
    """Run self-tests."""
    print("Self-test: branch_lifecycle.py")

    # Test 1: list_jarvis_branches returns list
    print("Test 1: list_jarvis_branches returns a list...")
    branches = list_jarvis_branches()
    assert isinstance(branches, list), "Expected list"
    for b in branches:
        assert any(b.startswith(p) for p in BRANCH_PREFIXES), f"Unexpected prefix: {b}"
    print(f"  PASS: {len(branches)} branches found")

    # Test 2: scan_branches returns correct structure
    print("Test 2: scan_branches returns correct structure...")
    results = scan_branches()
    assert isinstance(results, list), "Expected list"
    for r in results:
        assert "name" in r, "Missing name"
        if "error" not in r:
            assert "age_days" in r, f"Missing age_days for {r['name']}"
            assert "is_stale" in r, f"Missing is_stale for {r['name']}"
            assert "is_merged" in r, f"Missing is_merged for {r['name']}"
            assert isinstance(r["age_days"], int), f"age_days should be int for {r['name']}"
    print(f"  PASS: {len(results)} branches scanned")

    # Test 3: format_report produces output
    print("Test 3: format_report produces output...")
    report = format_report(results)
    assert isinstance(report, str), "Expected string"
    assert len(report) > 0, "Report should not be empty"
    print(f"  PASS: report is {len(report)} chars")

    # Test 4: format_report handles empty list
    print("Test 4: format_report handles empty list...")
    empty_report = format_report([])
    assert "No Jarvis" in empty_report, "Should say no branches"
    print("  PASS: empty list handled")

    # Test 5: collector interface
    print("Test 5: collector interface...")
    result = collect_stale_branches({"name": "test_stale"}, REPO_ROOT)
    assert result["name"] == "test_stale", f"Expected test_stale, got {result['name']}"
    assert result["unit"] == "count", f"Expected count unit"
    assert isinstance(result["value"], int), f"Expected int value, got {type(result['value'])}"
    print(f"  PASS: collector returned value={result['value']}")

    print(f"\nAll 5 tests passed.")


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main() -> None:
    args = sys.argv[1:]

    if "--self-test" in args:
        _self_test()
        return

    branches = scan_branches()

    if "--json" in args:
        print(json.dumps(branches, indent=2))
    else:
        print(format_report(branches))

    if "--notify" in args:
        notify_stale(branches)


if __name__ == "__main__":
    main()
