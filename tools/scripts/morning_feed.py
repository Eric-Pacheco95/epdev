#!/usr/bin/env python3
"""Jarvis Morning Feed -- combined briefing to Slack at 9am.

Uses claude -p (Claude Max subscription, no API key needed) for proposal
generation. Posts a single combined message to #epdev with: vitals snapshot,
learning progress, overnight diff summary, and 1-3 research proposals.

Usage:
    python tools/scripts/morning_feed.py                # full run
    python tools/scripts/morning_feed.py --dry-run      # preview, no Slack
    python tools/scripts/morning_feed.py --test          # self-test

Environment:
    SLACK_BOT_TOKEN    xoxb-... for Slack posting (required)

Outputs:
    memory/work/jarvis/morning_feed/YYYY-MM-DD.md   -- raw feed for audit
    Slack #epdev message                             -- combined briefing
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import urllib.error
import urllib.request
from datetime import datetime
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT))

# Absolute path to claude CLI -- Task Scheduler doesn't have .local/bin on PATH
_claude_candidate = Path(r"C:\Users\ericp\.local\bin\claude.exe")
CLAUDE_BIN = str(_claude_candidate) if _claude_candidate.is_file() else "claude"

SOURCES_FILE = REPO_ROOT / "memory" / "work" / "jarvis" / "sources.yaml"
STATE_FILE = REPO_ROOT / "data" / "overnight_state.json"
FEED_DIR = REPO_ROOT / "memory" / "work" / "jarvis" / "morning_feed"
HEARTBEAT_FILE = REPO_ROOT / "memory" / "work" / "isce" / "heartbeat_latest.json"
VALUE_FILE = REPO_ROOT / "data" / "autonomous_value.jsonl"


# -- Source loading -----------------------------------------------------------

def load_sources(tier: int = 1) -> list:
    """Load sources from sources.yaml for a given tier.

    Uses basic text parsing -- no pyyaml dependency.
    """
    if not SOURCES_FILE.is_file():
        return []

    text = SOURCES_FILE.read_text(encoding="utf-8")
    sources = []
    current = {}

    for line in text.splitlines():
        stripped = line.strip()

        if stripped.startswith("- name:"):
            if current and current.get("tier") == tier:
                sources.append(current)
            current = {"name": stripped.split(":", 1)[1].strip().strip('"')}

        elif stripped.startswith("url:") and current:
            current["url"] = stripped.split(":", 1)[1].strip().strip('"')
            # Fix for URLs -- "url:" splits on first colon, losing protocol
            if not current["url"].startswith("http"):
                current["url"] = "https:" + stripped.split(":", 2)[2].strip().strip('"')

        elif stripped.startswith("type:") and current:
            current["type"] = stripped.split(":", 1)[1].strip()

        elif stripped.startswith("tier:") and current:
            try:
                current["tier"] = int(stripped.split(":", 1)[1].strip())
            except ValueError:
                pass

        elif stripped.startswith("frequency:") and current:
            current["frequency"] = stripped.split(":", 1)[1].strip()

    # Don't forget last entry
    if current and current.get("tier") == tier:
        sources.append(current)

    return sources


# -- Vitals snapshot ----------------------------------------------------------

def get_vitals_snapshot() -> str:
    """Build a quick vitals summary from heartbeat data."""
    lines = []

    # Heartbeat data
    if HEARTBEAT_FILE.is_file():
        try:
            hb = json.loads(HEARTBEAT_FILE.read_text(encoding="utf-8"))
            metrics = hb.get("metrics", {})

            # ISC ratio
            isc_pass = metrics.get("isc_pass_count", {}).get("value", "?")
            isc_total = metrics.get("isc_total_count", {}).get("value", "?")
            lines.append(f"ISC: {isc_pass}/{isc_total}")

            # Signal count
            sig = metrics.get("signal_count", {}).get("value", "?")
            lines.append(f"Signals: {sig}")

            # Test health
            test_pass = metrics.get("test_pass_count", {}).get("value", "?")
            lines.append(f"Tests passing: {test_pass}")

        except (json.JSONDecodeError, OSError):
            lines.append("Heartbeat: unavailable")
    else:
        lines.append("Heartbeat: no data")

    # Overnight state
    if STATE_FILE.is_file():
        try:
            state = json.loads(STATE_FILE.read_text(encoding="utf-8"))
            last_dim = state.get("last_dimension", "none")
            last_date = state.get("last_run_date", "never")
            run_count = state.get("run_count", 0)
            lines.append(f"Overnight: last={last_dim} ({last_date}), total runs={run_count}")
        except (json.JSONDecodeError, OSError):
            lines.append("Overnight: no state")

    return " | ".join(lines)


# -- Overnight report --------------------------------------------------------

def get_overnight_summary() -> str:
    """Read the overnight run report for today's diff summary."""
    today = datetime.now().strftime("%Y-%m-%d")
    report_dir = (REPO_ROOT / "memory" / "work" / "jarvis" / "autoresearch"
                  / f"overnight-{today}")

    if not report_dir.is_dir():
        return "No overnight run today."

    report_file = report_dir / "report.md"
    if report_file.is_file():
        text = report_file.read_text(encoding="utf-8")
        # Return first 500 chars as summary
        if len(text) > 500:
            return text[:500] + "..."
        return text

    # Check for raw logs
    logs = list(report_dir.glob("*_raw.log"))
    if logs:
        return f"Overnight ran ({len(logs)} dimensions logged) but no structured report."

    return "Overnight directory exists but no reports found."


# -- GitHub source checking ---------------------------------------------------

def check_github_source(url: str) -> str:
    """Check a GitHub repo for recent activity via API."""
    # Extract owner/repo from URL
    m = re.match(r"https://github\.com/([^/]+)/([^/]+)", url)
    if not m:
        return ""

    owner, repo = m.group(1), m.group(2)
    api_url = f"https://api.github.com/repos/{owner}/{repo}/commits?per_page=3"

    try:
        req = urllib.request.Request(
            api_url,
            headers={"Accept": "application/vnd.github.v3+json",
                      "User-Agent": "Jarvis-MorningFeed/1.0"},
        )
        with urllib.request.urlopen(req, timeout=10) as resp:
            commits = json.loads(resp.read())
            if commits:
                latest = commits[0]
                date = latest.get("commit", {}).get("committer", {}).get("date", "")[:10]
                msg = latest.get("commit", {}).get("message", "").split("\n")[0][:80]
                return f"Latest commit ({date}): {msg}"
    except Exception:
        pass
    return ""


# -- Claude CLI call ----------------------------------------------------------

def call_claude(prompt: str, system: str = "") -> str:
    """Call claude -p for proposal generation. Uses Claude Max (no API key).

    Passes prompt via stdin to avoid Windows 32K command-line limit.
    Only safe from Task Scheduler or standalone CMD -- never from within
    an active Claude Code session (subprocess hang risk).
    """
    import subprocess

    if system:
        full_prompt = "SYSTEM INSTRUCTIONS:\n%s\n\nUSER INPUT:\n%s" % (system, prompt)
    else:
        full_prompt = prompt

    try:
        result = subprocess.run(
            [CLAUDE_BIN, "-p", "-"],
            input=full_prompt,
            capture_output=True,
            text=True,
            encoding="utf-8",
            timeout=120,
            cwd=str(REPO_ROOT),
        )
        if result.returncode == 0 and result.stdout.strip():
            return result.stdout.strip()
        if result.stderr.strip():
            return "(claude -p error: %s)" % result.stderr.strip()[:200]
        return "(claude -p returned empty response)"
    except FileNotFoundError as exc:
        return "(claude CLI not found: %s)" % exc
    except subprocess.TimeoutExpired:
        return "(claude -p timed out after 120s)"
    except Exception as exc:
        return "(claude -p failed: %s)" % exc


# -- Feed generation ---------------------------------------------------------

def generate_feed(dry_run: bool = False) -> str:
    """Generate the full morning feed content."""
    today = datetime.now().strftime("%Y-%m-%d")

    # 1. Vitals snapshot
    vitals = get_vitals_snapshot()

    # 2. Overnight summary
    overnight = get_overnight_summary()

    # 3. Check Tier 1 sources for recent activity
    sources = load_sources(tier=1)
    source_updates = []
    for src in sources:
        if src.get("type") == "github":
            update = check_github_source(src.get("url", ""))
            if update:
                source_updates.append(f"- {src['name']}: {update}")

    # 4. Build context for LLM to generate proposals
    source_context = "\n".join(source_updates) if source_updates else "No new updates from sources."

    # Read TELOS goals for cross-referencing
    telos_file = REPO_ROOT / "memory" / "work" / "TELOS.md"
    telos_summary = ""
    if telos_file.is_file():
        telos_text = telos_file.read_text(encoding="utf-8")
        # Extract just the goals section (first 500 chars)
        telos_summary = telos_text[:500]

    # 5. Call Anthropic API to rate and generate proposals
    system_prompt = """You are Jarvis, an AI assistant generating a morning briefing for Eric.

TASK: Review source updates and overnight results. Rate each item, then propose 1-3 actionable ideas from the highest-rated items only.

RATING SYSTEM (apply to each source update):
Rate each item S/A/B/C/D based on:
- S (exceptional): paradigm-shifting, directly enables a TELOS goal breakthrough
- A (high signal): concrete, actionable, clearly relevant to active projects or goals
- B (solid): useful context or pattern, worth knowing but not urgent
- C (filler): incremental update, no new insight
- D (noise): irrelevant or redundant

QUALITY GATE: Only propose items rated B+ or higher (S, A, or B). Drop C and D entirely.

OUTPUT FORMAT (plain text, no markdown headers or bold):
First, the rating breakdown:
RATINGS: [S] item1 | [A] item2 | [B+] item3 | [C] item4 (dropped) | ...

Then 1-3 numbered proposals from B+ items only. Each proposal must have:
- A title
- Which TELOS goal it connects to
- 2-3 sentences making the idea interesting and actionable (not just informational)

If no items pass B+, say: "No high-signal items today. Sources checked: N"

Keep total response under 300 words. Do not fabricate updates."""

    user_prompt = f"""Generate morning briefing proposals for {today}.

Source updates:
{source_context}

Overnight results:
{overnight}

TELOS goals context:
{telos_summary}

If source updates are thin today, suggest 1 idea based on overnight results or current project gaps instead."""

    if dry_run:
        proposals = f"[DRY RUN] Would call claude -p with {len(user_prompt)} char prompt"
    else:
        proposals = call_claude(user_prompt, system_prompt)

    # 6. Assemble combined message
    lines = [
        f"*Jarvis Morning Briefing -- {today}*",
        "",
        f"*Vitals:* {vitals}",
        "",
        f"*Overnight:* {overnight[:200]}",
        "",
        "*Today's Proposals:*",
        proposals,
    ]

    return "\n".join(lines)


# -- Main --------------------------------------------------------------------

def main() -> int:
    parser = argparse.ArgumentParser(description="Jarvis Morning Feed")
    parser.add_argument("--dry-run", action="store_true",
                        help="Preview feed without posting to Slack")
    parser.add_argument("--test", action="store_true",
                        help="Run self-tests")
    args = parser.parse_args()

    if args.test:
        return run_self_test()

    today = datetime.now().strftime("%Y-%m-%d")
    print(f"Jarvis Morning Feed -- {today}")

    # Dedup check: skip if already ran today (NFR-006)
    feed_file = FEED_DIR / f"{today}.md"
    if feed_file.is_file() and not args.dry_run:
        print(f"Already ran today ({today}). Feed exists at: {feed_file}")
        print("Use --dry-run to preview without posting.")
        return 0

    # Generate feed
    feed_content = generate_feed(dry_run=args.dry_run)

    # Save to audit file
    FEED_DIR.mkdir(parents=True, exist_ok=True)
    feed_file = FEED_DIR / f"{today}.md"
    feed_file.write_text(feed_content, encoding="utf-8")
    print(f"Feed saved to: {feed_file}")

    if args.dry_run:
        print("\n--- PREVIEW ---")
        print(feed_content)
        print("--- END PREVIEW ---")
        return 0

    # Post to Slack
    try:
        from tools.scripts.slack_notify import notify, EPDEV
        ok = notify(feed_content, EPDEV)
        if ok:
            print("Posted to #epdev Slack")
        else:
            print("Failed to post to Slack", file=sys.stderr)
    except ImportError:
        print("slack_notify not available", file=sys.stderr)

    # Track proposal IDs for value tracking
    track_proposals(today, feed_content)

    print(f"Morning feed complete.")
    return 0


def track_proposals(date: str, content: str) -> None:
    """Write proposal IDs to autonomous_value.jsonl for tracking."""
    # Count numbered proposals in content
    proposals = re.findall(r"^\d+\.", content, re.MULTILINE)
    VALUE_FILE.parent.mkdir(parents=True, exist_ok=True)

    for i, _ in enumerate(proposals, 1):
        entry = {
            "proposal_id": f"feed-{date}-{i:03d}",
            "date": date,
            "acted_on": False,
            "reference_session": None,
        }
        with open(VALUE_FILE, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry) + "\n")


# -- Self-test ---------------------------------------------------------------

def run_self_test() -> int:
    """Quick self-tests."""
    passed = 0
    failed = 0

    def check(condition, label):
        nonlocal passed, failed
        if condition:
            print(f"  PASS: {label}")
            passed += 1
        else:
            print(f"  FAIL: {label}")
            failed += 1

    print("Morning Feed -- Self-Test")
    print()

    # Source loading
    sources = load_sources(tier=1)
    check(len(sources) >= 5, f"Tier 1 sources >= 5 ({len(sources)} found)")

    tier2 = load_sources(tier=2)
    check(len(tier2) >= 3, f"Tier 2 sources >= 3 ({len(tier2)} found)")

    # Source fields
    if sources:
        src = sources[0]
        check("name" in src, "Source has name field")
        check("url" in src, "Source has url field")
        check("type" in src, "Source has type field")

    # Vitals snapshot
    vitals = get_vitals_snapshot()
    check(len(vitals) > 0, "Vitals snapshot produces output")

    # Feed directory
    check(SOURCES_FILE.is_file(), "sources.yaml exists")

    print()
    print(f"Results: {passed} passed, {failed} failed")
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
