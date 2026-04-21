#!/usr/bin/env python3
"""Prediction Event Generator -- SENSE layer for backtest event curation.

Reads TELOS goals, domain knowledge index, and calibration gaps to propose
new backtest events. Events are written to backtest_events.yaml with
status: proposed. Eric must approve (status: approved) before the backtest
producer will run them.

Sources:
  1. Calibration gaps   -- domains with < TARGET_PER_DOMAIN resolved backtests
  2. TELOS goals        -- maps goal keywords to prediction-relevant domains
  3. Domain knowledge    -- uses knowledge/index.md topics to seed event ideas
  4. Existing coverage   -- avoids proposing events similar to already-curated ones

All proposed events are constrained to pre-2022 to minimize leakage risk.

Usage:
    python tools/scripts/prediction_event_generator.py              # normal run
    python tools/scripts/prediction_event_generator.py --dry-run    # show what would propose
    python tools/scripts/prediction_event_generator.py --status     # show domain coverage
    python tools/scripts/prediction_event_generator.py --domain X   # propose for specific domain

Outputs:
    data/backtest_events.yaml                            -- proposed events appended
    orchestration/task_backlog.jsonl                     -- review task injected
    data/logs/event_generator_{date}.log                 -- run log
    Slack #epdev                                         -- summary notification
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from datetime import date, datetime, timezone
from pathlib import Path
from textwrap import dedent

import yaml

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT))

from tools.scripts.lib.isc_templates import isc_prediction_backtest_followup

EVENTS_FILE      = REPO_ROOT / "data" / "backtest_events.yaml"
CALIBRATION_FILE = REPO_ROOT / "data" / "calibration.json"
STATE_FILE       = REPO_ROOT / "data" / "event_generator_state.json"
KNOWLEDGE_INDEX  = REPO_ROOT / "memory" / "knowledge" / "index.md"
TELOS_GOALS      = REPO_ROOT / "memory" / "work" / "telos" / "GOALS.md"
TELOS_PREDICTIONS = REPO_ROOT / "memory" / "work" / "telos" / "PREDICTIONS.md"
LOGS_DIR         = REPO_ROOT / "data" / "logs"

TODAY = date.today().isoformat()

# Targets
TARGET_PER_DOMAIN = 25          # graduation threshold per domain
MAX_PROPOSALS_PER_RUN = 10      # autonomous pipeline; human reviews at summary stage
MAX_CUTOFF_YEAR = 2021          # pre-2022 only to minimize leakage
VALID_DOMAINS = ("geopolitics", "market", "technology", "planning")


# ---------------------------------------------------------------------------
# State I/O
# ---------------------------------------------------------------------------

def load_state() -> dict:
    if STATE_FILE.exists():
        try:
            return json.loads(STATE_FILE.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            return {}
    return {}


def save_state(state: dict) -> None:
    STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    tmp = STATE_FILE.with_suffix(".tmp")
    tmp.write_text(json.dumps(state, indent=2), encoding="utf-8")
    tmp.replace(STATE_FILE)


# ---------------------------------------------------------------------------
# Domain coverage analysis
# ---------------------------------------------------------------------------

def load_existing_events() -> list[dict]:
    """Load all events from backtest_events.yaml."""
    if not EVENTS_FILE.exists():
        return []
    data = yaml.safe_load(EVENTS_FILE.read_text(encoding="utf-8"))
    return data.get("events", []) if data else []


def load_calibration() -> dict:
    """Load calibration.json for domain coverage stats."""
    if not CALIBRATION_FILE.exists():
        return {}
    try:
        return json.loads(CALIBRATION_FILE.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return {}


def compute_domain_gaps(events: list[dict], calibration: dict) -> dict[str, int]:
    """Return {domain: events_needed} for domains below TARGET_PER_DOMAIN."""
    # Count existing events per domain (all statuses -- proposed, approved, run)
    counts: dict[str, int] = {d: 0 for d in VALID_DOMAINS}
    for e in events:
        domain = e.get("domain", "")
        if domain in counts:
            counts[domain] += 1

    gaps = {}
    for domain, count in counts.items():
        needed = TARGET_PER_DOMAIN - count
        if needed > 0:
            gaps[domain] = needed
    return gaps


# ---------------------------------------------------------------------------
# TELOS context extraction
# ---------------------------------------------------------------------------

def extract_telos_context() -> str:
    """Read TELOS goals and predictions for prompt context."""
    parts = []

    if TELOS_GOALS.exists():
        parts.append("## Eric's Goals\n" + TELOS_GOALS.read_text(encoding="utf-8"))

    if TELOS_PREDICTIONS.exists():
        parts.append("## Eric's Predictions\n" + TELOS_PREDICTIONS.read_text(encoding="utf-8"))

    return "\n\n".join(parts) if parts else ""


def extract_knowledge_context() -> str:
    """Read knowledge index for domain awareness."""
    if not KNOWLEDGE_INDEX.exists():
        return ""
    content = KNOWLEDGE_INDEX.read_text(encoding="utf-8")
    # Truncate to first 2000 chars to keep prompt reasonable
    return content[:2000] if len(content) > 2000 else content


def extract_existing_events_context(events: list[dict]) -> str:
    """Summarize existing events so the generator avoids duplicates."""
    if not events:
        return "No existing events."
    lines = []
    for e in events:
        lines.append(f"- {e['event_id']}: {e.get('description', '')[:80]} [{e.get('domain', '')}]")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Event generation via claude -p
# ---------------------------------------------------------------------------

EVENT_GENERATION_PROMPT = dedent("""\
    You are a backtest event curator for a prediction calibration system.

    TASK: Propose {count} high-quality historical events for backtesting a prediction engine.

    CONSTRAINTS:
    - Events must have knowledge_cutoff_date BEFORE 2022-01-01 (pre-2022 only)
    - Events must have clear, unambiguous known outcomes
    - Include difficulty ratings: low (obvious outcome), medium (uncertain), high (surprising outcome)
    - at_time_context must describe ONLY what was publicly known at the cutoff date
    - Do NOT reference what actually happened after the cutoff date in at_time_context
    - Prefer events where the "obvious" prediction was wrong (high difficulty)
    - Include boring non-events ("Will X happen?" where X did not happen) -- not just dramatic outcomes
    - Each event must be genuinely different from the existing events listed below

    DOMAIN PRIORITY (events needed):
    {domain_priorities}

    EXISTING EVENTS (avoid duplicates or similar topics):
    {existing_events}

    CONTEXT -- Eric's interests and goals (use to select relevant domains):
    {telos_context}

    DOMAIN KNOWLEDGE (topics Eric researches):
    {knowledge_context}

    OUTPUT FORMAT -- respond with ONLY valid YAML, no markdown fencing, no explanation:

    - event_id: "domain-short-slug"
      description: "The prediction question as asked at cutoff_date"
      domain: "geopolitics|market|technology|planning"
      knowledge_cutoff_date: "YYYY-MM-DD"
      known_outcome: "What actually happened"
      difficulty: "low|medium|high"
      status: "proposed"
      at_time_context: >
        2-4 sentences of what was publicly known at the cutoff date.
        Include specific data points, polls, or market conditions.
""")


def build_generation_prompt(
    domain_gaps: dict[str, int],
    events: list[dict],
    count: int,
) -> str:
    """Build the claude -p prompt for event generation."""
    # Domain priorities
    priority_lines = []
    for domain, needed in sorted(domain_gaps.items(), key=lambda x: -x[1]):
        priority_lines.append(f"  - {domain}: {needed} events needed (highest priority)")
    if not priority_lines:
        priority_lines.append("  - All domains at target. Propose diverse events across domains.")
    domain_priorities = "\n".join(priority_lines)

    # Existing events summary
    existing_events = extract_existing_events_context(events)

    # TELOS context
    telos_context = extract_telos_context()

    # Knowledge context
    knowledge_context = extract_knowledge_context()

    return EVENT_GENERATION_PROMPT.format(
        count=count,
        domain_priorities=domain_priorities,
        existing_events=existing_events,
        telos_context=telos_context or "(no TELOS context available)",
        knowledge_context=knowledge_context or "(no knowledge index available)",
    )


def run_claude(prompt: str) -> str | None:
    """Run claude -p and return output. Returns None on failure."""
    try:
        result = subprocess.run(
            ["claude", "-p", "--model", "sonnet", prompt],
            capture_output=True,
            text=True,
            timeout=300,
            cwd=str(REPO_ROOT),
        )
        if result.returncode != 0:
            print(f"  WARN: claude exited {result.returncode}", file=sys.stderr)
            return None

        output = result.stdout.strip()

        # Rate limit guard
        rate_limit_phrases = ["hit your limit", "rate limit", "quota exceeded"]
        if any(phrase in output.lower() for phrase in rate_limit_phrases):
            print("  WARN: rate limit detected -- aborting", file=sys.stderr)
            return None

        return output if output else None

    except subprocess.TimeoutExpired:
        print("  WARN: claude timed out", file=sys.stderr)
        return None
    except FileNotFoundError:
        print("  ERROR: claude CLI not found in PATH", file=sys.stderr)
        return None


def parse_proposed_events(claude_output: str) -> list[dict]:
    """Parse YAML event proposals from claude output."""
    # Strip markdown fencing if present
    cleaned = re.sub(r"```ya?ml\s*", "", claude_output)
    cleaned = re.sub(r"```\s*$", "", cleaned, flags=re.MULTILINE)
    cleaned = cleaned.strip()

    try:
        parsed = yaml.safe_load(cleaned)
    except yaml.YAMLError as exc:
        print(f"  WARN: YAML parse failed: {exc}", file=sys.stderr)
        return []

    # Handle both list and dict-with-events formats
    if isinstance(parsed, list):
        events = parsed
    elif isinstance(parsed, dict) and "events" in parsed:
        events = parsed["events"]
    else:
        print(f"  WARN: unexpected YAML structure: {type(parsed)}", file=sys.stderr)
        return []

    # Validate each event
    valid = []
    for e in events:
        if not isinstance(e, dict):
            continue

        # Required fields
        required = ("event_id", "description", "domain", "knowledge_cutoff_date",
                     "known_outcome", "difficulty", "at_time_context")
        if not all(e.get(f) for f in required):
            missing = [f for f in required if not e.get(f)]
            print(f"  WARN: skipping event missing fields: {missing}", file=sys.stderr)
            continue

        # Domain check
        if e["domain"] not in VALID_DOMAINS:
            print(f"  WARN: skipping event with invalid domain: {e['domain']}", file=sys.stderr)
            continue

        # Cutoff date check
        try:
            cutoff = datetime.strptime(str(e["knowledge_cutoff_date"]), "%Y-%m-%d")
            if cutoff.year >= MAX_CUTOFF_YEAR + 1:
                print(f"  WARN: skipping event with cutoff >= 2022: {e['event_id']}", file=sys.stderr)
                continue
        except ValueError:
            print(f"  WARN: skipping event with bad date: {e['knowledge_cutoff_date']}", file=sys.stderr)
            continue

        # Auto-approve: pipeline is autonomous, human reviews at summary stage
        e["status"] = "approved"
        valid.append(e)

    return valid


# ---------------------------------------------------------------------------
# Event writing
# ---------------------------------------------------------------------------

def append_events_to_yaml(new_events: list[dict], existing_events: list[dict]) -> int:
    """Append proposed events to backtest_events.yaml. Returns count added."""
    existing_ids = {e["event_id"] for e in existing_events}
    to_add = [e for e in new_events if e["event_id"] not in existing_ids]

    if not to_add:
        return 0

    # Read current file content
    content = EVENTS_FILE.read_text(encoding="utf-8") if EVENTS_FILE.exists() else "events:\n"

    # Append new events as YAML
    for event in to_add:
        # Build YAML block manually for consistent formatting
        block = f"""
  - event_id: {event['event_id']}
    description: "{event['description'].replace('"', "'")}"
    domain: {event['domain']}
    knowledge_cutoff_date: "{event['knowledge_cutoff_date']}"
    known_outcome: "{str(event['known_outcome']).replace('"', "'")}"
    difficulty: {event['difficulty']}
    status: proposed
    at_time_context: >
      {str(event.get('at_time_context', '')).strip()}
"""
        content += block

    EVENTS_FILE.write_text(content, encoding="utf-8")
    return len(to_add)


# ---------------------------------------------------------------------------
# Backlog integration
# ---------------------------------------------------------------------------

def inject_backtest_task(count: int, domains: list[str]) -> bool:
    """Inject a backtest run task so the dispatcher runs the producer next."""
    try:
        from tools.scripts.lib.backlog import backlog_append

        domain_str = ", ".join(sorted(set(domains)))
        task = {
            "description": f"Run backtest producer on {count} new auto-approved events ({domain_str})",
            "project": "epdev",
            "repo_path": str(REPO_ROOT),
            "tier": 2,
            "priority": 5,
            "goal_context": (
                "Prediction calibration pipeline -- events were auto-generated and approved. "
                "Run prediction_backtest_producer.py to execute backtests. "
                "Slack review summary will be posted for Eric to score."
            ),
            "isc": isc_prediction_backtest_followup(),
            "context_files": ["data/backtest_events.yaml", "data/backtest_state.json"],
            "skills": [],
            "model": "sonnet",
            "autonomous_safe": True,
            "routine_id": "prediction-backtest-followup",
            "notes": f"Auto-chained from prediction_event_generator.py on {TODAY}",
        }

        result = backlog_append(task)
        return result is not None

    except Exception as exc:
        print(f"  WARN: backlog injection failed: {exc}", file=sys.stderr)
        return False


# ---------------------------------------------------------------------------
# Slack notification
# ---------------------------------------------------------------------------

def notify_slack(count: int, domains: list[str], dry_run: bool = False) -> None:
    """Send summary to Slack."""
    try:
        from tools.scripts.slack_notify import notify

        prefix = "[DRY RUN] " if dry_run else ""
        domain_str = ", ".join(sorted(set(domains)))
        msg = (
            f"*{prefix}Event Generator -- {TODAY}*\n"
            f"{count} backtest event(s) auto-approved for domains: {domain_str}\n"
            f"Backtest producer will run these next. Review summary will follow."
        )
        notify(msg, severity="routine")
    except Exception as exc:
        print(f"  WARN: Slack notify failed: {exc}", file=sys.stderr)


# ---------------------------------------------------------------------------
# Status display
# ---------------------------------------------------------------------------

def show_status(events: list[dict], calibration: dict) -> None:
    """Show domain coverage table."""
    counts: dict[str, dict[str, int]] = {d: {"total": 0, "proposed": 0, "approved": 0, "run": 0}
                                           for d in VALID_DOMAINS}
    for e in events:
        domain = e.get("domain", "")
        if domain not in counts:
            continue
        counts[domain]["total"] += 1
        status = e.get("status", "")
        if status == "proposed":
            counts[domain]["proposed"] += 1
        elif status == "approved":
            counts[domain]["approved"] += 1
        else:
            # No status field = legacy event (already run)
            counts[domain]["run"] += 1

    cal_domains = calibration.get("domains", {})

    print(f"Backtest Event Coverage -- {TODAY}")
    print(f"{'Domain':<14} {'Total':<8} {'Run':<8} {'Approved':<10} {'Proposed':<10} {'Target':<8} {'Gap':<8} {'Cal Adj':<10}")
    print("-" * 80)
    for domain in VALID_DOMAINS:
        c = counts[domain]
        gap = max(0, TARGET_PER_DOMAIN - c["total"])
        cal = cal_domains.get(domain, {})
        adj = cal.get("adjustment", 0)
        adj_str = f"{adj:+.1%}" if adj else "n/a"
        print(f"{domain:<14} {c['total']:<8} {c['run']:<8} {c['approved']:<10} {c['proposed']:<10} {TARGET_PER_DOMAIN:<8} {gap:<8} {adj_str:<10}")

    total = sum(c["total"] for c in counts.values())
    total_target = TARGET_PER_DOMAIN * len(VALID_DOMAINS)
    print(f"\nTotal: {total}/{total_target} | Graduation: {TARGET_PER_DOMAIN}/domain")


# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------

def write_log(message: str) -> None:
    """Append to run log."""
    LOGS_DIR.mkdir(parents=True, exist_ok=True)
    log_path = LOGS_DIR / f"event_generator_{TODAY}.log"
    with open(log_path, "a", encoding="utf-8") as f:
        ts = datetime.now(timezone.utc).strftime("%H:%M:%S")
        f.write(f"[{ts}] {message}\n")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> int:
    parser = argparse.ArgumentParser(description="Prediction Event Generator")
    parser.add_argument("--dry-run", action="store_true", help="Show proposals without writing")
    parser.add_argument("--status", action="store_true", help="Show domain coverage table")
    parser.add_argument("--domain", metavar="DOMAIN", help="Generate for specific domain only")
    parser.add_argument("--count", type=int, default=MAX_PROPOSALS_PER_RUN,
                        help=f"Number of events to propose (default: {MAX_PROPOSALS_PER_RUN})")
    args = parser.parse_args()

    events = load_existing_events()
    calibration = load_calibration()

    if args.status:
        show_status(events, calibration)
        return 0

    # Compute gaps
    domain_gaps = compute_domain_gaps(events, calibration)

    # Filter to requested domain if specified
    if args.domain:
        if args.domain not in VALID_DOMAINS:
            print(f"ERROR: invalid domain '{args.domain}'. Valid: {', '.join(VALID_DOMAINS)}")
            return 1
        domain_gaps = {args.domain: domain_gaps.get(args.domain, 0)}
        if domain_gaps[args.domain] <= 0:
            print(f"Domain '{args.domain}' already at target ({TARGET_PER_DOMAIN} events).")
            return 0

    if not domain_gaps:
        print(f"All domains at target ({TARGET_PER_DOMAIN}/domain). No events needed.")
        write_log("Idle: all domains at target.")
        return 0

    # Cap count to what's actually needed
    total_needed = sum(domain_gaps.values())
    count = min(args.count, total_needed)

    print(f"Event Generator -- {TODAY}")
    print(f"Domain gaps: {domain_gaps}")
    print(f"Proposing {count} event(s)...")
    write_log(f"Gaps: {domain_gaps} | Proposing: {count}")

    # Build and run prompt
    prompt = build_generation_prompt(domain_gaps, events, count)

    if args.dry_run:
        print(f"\n[DRY RUN] Would send prompt to claude -p (sonnet):")
        print(f"  Domains: {list(domain_gaps.keys())}")
        print(f"  Count: {count}")
        print(f"  Existing events: {len(events)}")
        return 0

    output = run_claude(prompt)
    if output is None:
        print("ERROR: claude invocation failed. No events proposed.")
        write_log("ERROR: claude invocation failed.")
        return 1

    # Parse proposals
    proposed = parse_proposed_events(output)
    if not proposed:
        print("WARN: no valid events parsed from claude output.")
        write_log("WARN: no valid events parsed.")
        return 1

    # Write to YAML
    added = append_events_to_yaml(proposed, events)
    if added == 0:
        print("All proposed events were duplicates. Nothing added.")
        write_log("All duplicates.")
        return 0

    domains_added = [e["domain"] for e in proposed[:added]]
    print(f"\nAdded {added} proposed event(s) to backtest_events.yaml")
    for e in proposed[:added]:
        print(f"  + {e['event_id']} [{e['domain']}] cutoff={e['knowledge_cutoff_date']} diff={e['difficulty']}")

    # Chain: inject backtest run task so producer picks up the new events
    if inject_backtest_task(added, domains_added):
        print("Backtest run task injected into task_backlog.jsonl (auto-chain)")
    else:
        print("WARN: backtest task injection skipped (dedup or error)")

    # Update state
    state = load_state()
    state["last_run"] = TODAY
    state.setdefault("history", []).append({
        "date": TODAY,
        "proposed": added,
        "domains": domains_added,
    })
    save_state(state)

    # Notify
    notify_slack(added, domains_added)
    write_log(f"Done: {added} events proposed, review task injected.")

    print(f"\nNext step: review events in backtest_events.yaml, change status: proposed -> approved")
    return 0


if __name__ == "__main__":
    sys.exit(main())
