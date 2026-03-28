#!/usr/bin/env python3
"""Jarvis health report — aggregate JSONL event files into the 5 core health metrics.

Usage:
  python tools/scripts/query_events.py              # full report, last 7 days
  python tools/scripts/query_events.py --days 30    # longer window
  python tools/scripts/query_events.py --isc-gaps   # ISC gap detail only
  python tools/scripts/query_events.py --failures   # tool failure breakdown
  python tools/scripts/query_events.py --cost        # session cost summary (when available)
  python tools/scripts/query_events.py --json        # machine-readable output (for Phase 3E)

Metrics:
  1. sessions/day      — Stop records per day (session boundaries)
  2. tool_failure_rate — PostToolUse failures / total PostToolUse calls
  3. isc_gap_count     — PostToolUse failures per session (proxy for ISC gaps)
  4. top_tools         — tool call frequency histogram
  5. cost              — session cost in USD (requires Stop hook cost data; N/A until wired)

Phase 3E: --json outputs a dict that the heartbeat can compare against ISC thresholds.
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter, defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
EVENTS_DIR = REPO_ROOT / "history" / "events"

# Health thresholds — adjust in Phase 3E ISC engine
THRESHOLDS = {
    "failure_rate_warn": 0.05,   # 5% failures = WARN
    "failure_rate_crit": 0.15,   # 15% failures = CRITICAL
    "sessions_per_day_min": 0.5, # less than 1 session every 2 days = WARN (usage gap)
}


def load_records(days: int) -> list[dict]:
    """Load JSONL records from the last N days."""
    cutoff = datetime.now(timezone.utc) - timedelta(days=days)
    records = []
    if not EVENTS_DIR.exists():
        return records
    for path in sorted(EVENTS_DIR.glob("*.jsonl")):
        try:
            file_date = datetime.strptime(path.stem, "%Y-%m-%d").replace(tzinfo=timezone.utc)
        except ValueError:
            continue
        if file_date < cutoff - timedelta(days=1):
            continue
        with path.open(encoding="utf-8") as fh:
            for line in fh:
                line = line.strip()
                if not line:
                    continue
                try:
                    rec = json.loads(line)
                    ts = datetime.strptime(rec["ts"], "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
                    if ts >= cutoff:
                        records.append(rec)
                except (json.JSONDecodeError, KeyError, ValueError):
                    continue
    return records


def compute_metrics(records: list[dict]) -> dict:
    post_tool = [r for r in records if r.get("hook") == "PostToolUse" and r.get("tool") != "_session"]
    pre_tool  = [r for r in records if r.get("hook") == "PreToolUse"]
    stops     = [r for r in records if r.get("hook") == "Stop" or r.get("tool") == "_session"]

    # 1. Sessions/day
    session_days: set[str] = set()
    session_ids: set[str] = set()
    for r in stops:
        session_ids.add(r.get("session_id", ""))
        ts = r.get("ts", "")[:10]
        if ts:
            session_days.add(ts)

    # Fallback: if no Stop records, estimate from unique session_ids in PostToolUse
    if not session_ids:
        for r in post_tool:
            session_ids.add(r.get("session_id", ""))

    unique_days = len({r.get("ts", "")[:10] for r in records if r.get("ts")}) or 1
    sessions_total = len(session_ids - {""})
    sessions_per_day = round(sessions_total / unique_days, 2)

    # 2. Tool failure rate
    total_calls = len(post_tool)
    failures = [r for r in post_tool if r.get("success") is False]
    failure_count = len(failures)
    failure_rate = round(failure_count / total_calls, 4) if total_calls else 0.0

    # 3. ISC gaps — failures per session (proxy: sessions with ≥1 failure)
    session_failures: dict[str, list] = defaultdict(list)
    for r in failures:
        session_failures[r.get("session_id", "unknown")].append(r.get("tool", "?"))
    isc_gap_sessions = len(session_failures)

    # 4. Top tools
    tool_counts = Counter(r.get("tool", "?") for r in post_tool)
    top_tools = tool_counts.most_common(10)

    # 5. Cost — read from Stop records if hook_events writes cost_usd field
    cost_records = [r for r in stops if r.get("cost_usd") is not None]
    total_cost = sum(r["cost_usd"] for r in cost_records)
    avg_cost = round(total_cost / len(cost_records), 4) if cost_records else None

    # Intent calls (PreToolUse)
    intent_calls = len(pre_tool)

    return {
        "sessions_total": sessions_total,
        "sessions_per_day": sessions_per_day,
        "total_tool_calls": total_calls,
        "failure_count": failure_count,
        "failure_rate": failure_rate,
        "isc_gap_sessions": isc_gap_sessions,
        "session_failures": dict(session_failures),
        "top_tools": top_tools,
        "intent_calls": intent_calls,
        "cost_total_usd": round(total_cost, 4) if cost_records else None,
        "cost_avg_per_session_usd": avg_cost,
        "cost_sessions_tracked": len(cost_records),
        "unique_days_with_data": unique_days,
    }


def status_badge(metric: str, value: float) -> str:
    if metric == "failure_rate":
        if value >= THRESHOLDS["failure_rate_crit"]:
            return "CRITICAL"
        if value >= THRESHOLDS["failure_rate_warn"]:
            return "WARN"
        return "OK"
    if metric == "sessions_per_day":
        if value < THRESHOLDS["sessions_per_day_min"]:
            return "WARN"
        return "OK"
    return "OK"


def print_report(m: dict, days: int) -> None:
    fail_pct = f"{m['failure_rate'] * 100:.1f}%"
    fail_status = status_badge("failure_rate", m["failure_rate"])
    session_status = status_badge("sessions_per_day", m["sessions_per_day"])

    # Overall status
    overall = "HEALTHY"
    if "CRITICAL" in [fail_status]:
        overall = "CRITICAL"
    elif "WARN" in [fail_status, session_status]:
        overall = "WARN"

    cost_line = "N/A (Stop cost hook not yet wired)"
    if m["cost_total_usd"] is not None:
        cost_line = (
            f"${m['cost_total_usd']:.4f} total  "
            f"(${m['cost_avg_per_session_usd']:.4f}/session avg, "
            f"{m['cost_sessions_tracked']} sessions tracked)"
        )

    top_tools_str = "  ".join(f"{t}({c})" for t, c in m["top_tools"][:7])

    print(f"\nJarvis Health -- last {days} days  ({m['unique_days_with_data']} days with data)")
    print("-" * 60)
    print(f"Sessions:     {m['sessions_total']} total  ({m['sessions_per_day']}/day avg)  [{session_status}]")
    print(f"Tool calls:   {m['total_tool_calls']} total  {m['failure_count']} failures  ({fail_pct} rate)  [{fail_status}]")
    print(f"Intent calls: {m['intent_calls']} PreToolUse recorded")
    print(f"ISC gaps:     {m['isc_gap_sessions']} sessions had >=1 failure")
    print(f"Cost:         {cost_line}")
    print(f"Top tools:    {top_tools_str}")
    print("-" * 60)
    print(f"Status: {overall}")

    if m["isc_gap_sessions"] > 0 and m["session_failures"]:
        print("\nSessions with failures:")
        for sid, tools in list(m["session_failures"].items())[:5]:
            sid_short = sid[:12] if sid else "unknown"
            print(f"  {sid_short}...  tools: {', '.join(tools)}")


def print_isc_gaps(m: dict) -> None:
    if not m["session_failures"]:
        print("No ISC gaps detected (0 tool failures).")
        return
    print(f"\nISC Gaps — {m['isc_gap_sessions']} session(s) with failures:\n")
    for sid, tools in m["session_failures"].items():
        sid_short = sid[:16] if sid else "unknown"
        tool_counts = Counter(tools)
        for tool, count in tool_counts.items():
            print(f"  {sid_short}  {tool:<20} {count} failure(s)")


def print_failures(records: list[dict]) -> None:
    failures = [r for r in records if r.get("hook") == "PostToolUse" and r.get("success") is False]
    if not failures:
        print("No tool failures in this window.")
        return
    by_tool = Counter(r.get("tool", "?") for r in failures)
    print(f"\nTool Failures — {len(failures)} total:\n")
    for tool, count in by_tool.most_common():
        print(f"  {tool:<25} {count:>4} failure(s)")
    print(f"\nSample error messages:")
    seen = set()
    for r in failures:
        tool = r.get("tool", "?")
        if tool not in seen and r.get("error"):
            print(f"  [{tool}] {r['error'][:100]}")
            seen.add(tool)


def print_cost(m: dict) -> None:
    if m["cost_total_usd"] is None:
        print("\nCost tracking: N/A")
        print("The Stop hook does not yet write cost_usd to JSONL.")
        print("Cost data will appear here once hook_session_cost.py is wired.")
    else:
        print(f"\nCost Summary:")
        print(f"  Total:      ${m['cost_total_usd']:.4f}")
        print(f"  Per session: ${m['cost_avg_per_session_usd']:.4f}")
        print(f"  Sessions tracked: {m['cost_sessions_tracked']}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Jarvis health report")
    parser.add_argument("--days", type=int, default=7, help="Look-back window in days (default: 7)")
    parser.add_argument("--isc-gaps", action="store_true", help="Show ISC gap detail")
    parser.add_argument("--failures", action="store_true", help="Show tool failure breakdown")
    parser.add_argument("--cost", action="store_true", help="Show cost summary")
    parser.add_argument("--json", action="store_true", help="Machine-readable JSON output (for Phase 3E)")
    args = parser.parse_args()

    records = load_records(args.days)
    if not records:
        print(f"No event records found in history/events/ for the last {args.days} days.")
        sys.exit(0)

    m = compute_metrics(records)

    if args.json:
        output = {k: v for k, v in m.items() if k != "session_failures"}
        output["isc_gap_sessions"] = m["isc_gap_sessions"]
        output["status"] = (
            "CRITICAL" if m["failure_rate"] >= THRESHOLDS["failure_rate_crit"]
            else "WARN" if (
                m["failure_rate"] >= THRESHOLDS["failure_rate_warn"]
                or m["sessions_per_day"] < THRESHOLDS["sessions_per_day_min"]
            )
            else "HEALTHY"
        )
        print(json.dumps(output, indent=2))
    elif args.isc_gaps:
        print_isc_gaps(m)
    elif args.failures:
        print_failures(records)
    elif args.cost:
        print_cost(m)
    else:
        print_report(m, args.days)


if __name__ == "__main__":
    main()
