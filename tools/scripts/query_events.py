#!/usr/bin/env python3
"""Jarvis health report -- aggregate JSONL event files into core health metrics.

Usage:
  python tools/scripts/query_events.py --report          # full health report, last 7 days
  python tools/scripts/query_events.py --cost            # cost summary only (session_cost records)
  python tools/scripts/query_events.py --failures        # tool failure breakdown
  python tools/scripts/query_events.py --isc-gaps        # ISC gap analysis (Phase 5)
  python tools/scripts/query_events.py --report --days 30  # longer window
  python tools/scripts/query_events.py --json            # machine-readable output (for Phase 3E)

Metrics:
  1. sessions/day      -- Stop records per day (session boundaries)
  2. tool_failure_rate -- PostToolUse failures / total PostToolUse calls
  3. top_tools         -- tool call frequency histogram
  4. cost              -- session cost in USD (from session_cost records; null until Claude Code exposes tokens)

Phase 3E: --json outputs a dict that the heartbeat can compare against ISC thresholds.
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter, defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Optional

REPO_ROOT = Path(__file__).resolve().parents[2]
EVENTS_DIR = REPO_ROOT / "history" / "events"

# Health thresholds --adjust in Phase 3E ISC engine
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

    # 3. ISC gaps --failures per session (proxy: sessions with >=1 failure)
    session_failures: dict[str, list] = defaultdict(list)
    for r in failures:
        session_failures[r.get("session_id", "unknown")].append(r.get("tool", "?"))
    isc_gap_sessions = len(session_failures)

    # 4. Top tools
    tool_counts = Counter(r.get("tool", "?") for r in post_tool)
    top_tools = tool_counts.most_common(10)

    # 5. Cost --read from session_cost records (hook_session_cost.py) or legacy Stop records
    cost_records = [r for r in records if r.get("type") == "session_cost"]
    # Also check legacy Stop records with cost_usd field
    legacy_cost = [r for r in stops if r.get("cost_usd") is not None and r.get("type") != "session_cost"]
    all_cost_records = cost_records + legacy_cost

    # Token aggregation from session_cost records
    input_tokens_total = sum(r["input_tokens"] for r in all_cost_records if r.get("input_tokens") is not None)
    output_tokens_total = sum(r["output_tokens"] for r in all_cost_records if r.get("output_tokens") is not None)
    cache_read_total = sum(r["cache_read_tokens"] for r in all_cost_records if r.get("cache_read_tokens") is not None)
    has_token_data = any(r.get("input_tokens") is not None for r in all_cost_records)

    records_with_cost = [r for r in all_cost_records if r.get("cost_usd") is not None]
    total_cost = sum(r["cost_usd"] for r in records_with_cost)
    avg_cost = round(total_cost / len(records_with_cost), 4) if records_with_cost else None

    # Also count session_cost records for session tracking
    for r in cost_records:
        sid = r.get("session_id", "")
        if sid:
            session_ids.add(sid)
    sessions_total = len(session_ids - {""})

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
        "cost_total_usd": round(total_cost, 4) if records_with_cost else None,
        "cost_avg_per_session_usd": avg_cost,
        "cost_sessions_tracked": len(all_cost_records),
        "input_tokens_total": input_tokens_total if has_token_data else None,
        "output_tokens_total": output_tokens_total if has_token_data else None,
        "cache_read_tokens_total": cache_read_total if has_token_data else None,
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


def _compute_date_range(days: int) -> tuple:
    """Return (start_date_str, end_date_str) for display."""
    now = datetime.now(timezone.utc)
    end = now.date()
    start = (now - timedelta(days=days)).date()
    return str(start), str(end)


def print_report(m: dict, days: int) -> None:
    start_str, end_str = _compute_date_range(days)
    fail_pct = f"{m['failure_rate'] * 100:.1f}%"
    fail_status = status_badge("failure_rate", m["failure_rate"])
    session_status = status_badge("sessions_per_day", m["sessions_per_day"])

    # Overall status
    overall = "HEALTHY"
    if "CRITICAL" in [fail_status]:
        overall = "CRITICAL"
    elif "WARN" in [fail_status, session_status]:
        overall = "WARN"

    # Status reason
    if overall == "HEALTHY":
        status_reason = "(failure rate < 5%)"
    elif overall == "WARN" and fail_status == "WARN":
        status_reason = "(failure rate 5-15%)"
    elif overall == "CRITICAL":
        status_reason = "(failure rate >= 15%)"
    else:
        status_reason = "(low session activity)"

    # Cost line
    cost_line = "unavailable (token tracking pending)"
    if m["cost_total_usd"] is not None:
        cost_line = (
            f"${m['cost_total_usd']:.2f} total "
            f"(${m['cost_avg_per_session_usd']:.4f}/session avg, "
            f"{m['cost_sessions_tracked']} sessions tracked)"
        )
    elif m["input_tokens_total"] is not None:
        cost_line = (
            f"{m['input_tokens_total']:,} input, "
            f"{m['output_tokens_total']:,} output tokens"
        )

    top_tools_str = " ".join(f"{t}({c})" for t, c in m["top_tools"][:5])
    if not top_tools_str:
        top_tools_str = "none"

    header = f"Jarvis Health -- {start_str} to {end_str}"
    separator = "-" * len(header)

    print(header)
    print(separator)
    print(f"Sessions:        {m['sessions_total']} sessions ({m['sessions_per_day']}/day avg)")
    print(f"Tool calls:      {m['total_tool_calls']} total, {m['failure_count']} failures ({fail_pct} failure rate)")
    print(f"Cost:            {cost_line}")
    print(f"Top tools:       {top_tools_str}")
    print(separator)
    print(f"Status: {overall}  {status_reason}")


def print_isc_gaps(m: dict) -> None:
    print("ISC gap detection requires more data. Coming in Phase 5.")


def print_failures(records: list[dict]) -> None:
    failures = [r for r in records if r.get("hook") == "PostToolUse" and r.get("success") is False]
    if not failures:
        print("No tool failures in this window.")
        return
    by_tool = Counter(r.get("tool", "?") for r in failures)
    print(f"\nTool Failures --{len(failures)} total:\n")
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
    start_str, end_str = _compute_date_range(7)  # uses default; caller could override
    header = f"Jarvis Cost Summary -- {start_str} to {end_str}"
    separator = "-" * len(header)
    print(header)
    print(separator)
    if m["cost_sessions_tracked"] == 0:
        print("No session_cost records found.")
    elif m["cost_total_usd"] is not None:
        print(f"Sessions tracked: {m['cost_sessions_tracked']}")
        print(f"Total cost:       ${m['cost_total_usd']:.2f}")
        print(f"Per session:      ${m['cost_avg_per_session_usd']:.4f}")
    else:
        print(f"Sessions tracked: {m['cost_sessions_tracked']}")
        print(f"Cost data:        unavailable (token tracking pending)")
    if m.get("input_tokens_total") is not None:
        print(f"Input tokens:     {m['input_tokens_total']:,}")
        print(f"Output tokens:    {m['output_tokens_total']:,}")
    print(separator)


def build_parser() -> argparse.ArgumentParser:
    """Build the argument parser."""
    parser = argparse.ArgumentParser(
        description="Query Jarvis observability events and produce health reports.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--report", action="store_true", help="Full health report (default)")
    group.add_argument("--cost", action="store_true", help="Cost summary only")
    group.add_argument("--failures", action="store_true", help="Tool failure breakdown")
    group.add_argument("--isc-gaps", action="store_true", help="ISC gap analysis (not yet implemented)")
    group.add_argument("--json", action="store_true", help="Machine-readable JSON output (for Phase 3E)")
    parser.add_argument("--days", type=int, default=7, help="Number of days to include (default: 7)")
    return parser


def run(args: Optional[argparse.Namespace] = None) -> str:
    """Execute the query and return the report as a string.

    Captures stdout so callers can use this as a library function.
    """
    import io
    if args is None:
        args = build_parser().parse_args()

    records = load_records(args.days)

    # Capture print output
    buf = io.StringIO()
    old_stdout = sys.stdout
    sys.stdout = buf

    try:
        if not records:
            print(f"No events found in history/events/ for the last {args.days} days.")
        elif args.json:
            m = compute_metrics(records)
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
            m = compute_metrics(records)
            print_isc_gaps(m)
        elif args.failures:
            print_failures(records)
        elif args.cost:
            m = compute_metrics(records)
            print_cost(m)
        else:
            # Default to --report
            m = compute_metrics(records)
            print_report(m, args.days)
    finally:
        sys.stdout = old_stdout

    return buf.getvalue().rstrip("\n")


def main() -> None:
    output = run()
    print(output)


if __name__ == "__main__":
    main()
