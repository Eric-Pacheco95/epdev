#!/usr/bin/env python3
"""Heartbeat history rotation -- keep raw entries for 30 days, summarize older.

Reads heartbeat_history.jsonl entries, partitions into recent (keep raw)
and old (aggregate into monthly summaries), then truncates the main file.

Usage:
    python tools/scripts/rotate_heartbeat.py              # dry-run
    python tools/scripts/rotate_heartbeat.py --execute    # actually rotate
    python tools/scripts/rotate_heartbeat.py --days 30    # custom retention

Monthly summaries written to memory/work/isce/heartbeat_monthly/YYYY-MM.json
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_CONFIG = REPO_ROOT / "heartbeat_config.json"
HISTORY_FILE = REPO_ROOT / "memory" / "work" / "isce" / "heartbeat_history.jsonl"
MONTHLY_DIR = REPO_ROOT / "memory" / "work" / "isce" / "heartbeat_monthly"


def load_retention_days(config_path: Path) -> int:
    """Read rollup_after_days from config, default 30."""
    if config_path.is_file():
        try:
            cfg = json.loads(config_path.read_text(encoding="utf-8"))
            return cfg.get("retention", {}).get("rollup_after_days", 30)
        except (json.JSONDecodeError, OSError):
            pass
    return 30


def parse_entries(history_path: Path) -> list[dict]:
    """Parse all JSONL entries, skipping malformed lines."""
    entries = []
    if not history_path.is_file():
        return entries
    with history_path.open(encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                entries.append(json.loads(line))
            except json.JSONDecodeError:
                continue
    return entries


def partition_entries(entries: list[dict], cutoff: datetime) -> tuple[list[dict], list[dict]]:
    """Split entries into (recent, old) based on timestamp vs cutoff."""
    recent = []
    old = []
    for entry in entries:
        ts_str = entry.get("ts", "")
        try:
            ts = datetime.strptime(ts_str, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
        except (ValueError, TypeError):
            # Can't parse timestamp -- keep it in recent to be safe
            recent.append(entry)
            continue
        if ts >= cutoff:
            recent.append(entry)
        else:
            old.append(entry)
    return recent, old


def aggregate_monthly(entries: list[dict]) -> dict[str, dict]:
    """Group old entries by YYYY-MM and compute min/max/avg per metric."""
    monthly: dict[str, list[dict]] = defaultdict(list)
    for entry in entries:
        ts_str = entry.get("ts", "")
        try:
            ts = datetime.strptime(ts_str, "%Y-%m-%dT%H:%M:%SZ")
            key = "%d-%02d" % (ts.year, ts.month)
        except (ValueError, TypeError):
            continue
        monthly[key].append(entry)

    summaries = {}
    for month_key, month_entries in sorted(monthly.items()):
        # Collect all numeric metric values
        metric_values: dict[str, list[float]] = defaultdict(list)
        for entry in month_entries:
            metrics = entry.get("metrics", {})
            for metric_name, metric_data in metrics.items():
                val = metric_data.get("value") if isinstance(metric_data, dict) else None
                if val is not None and isinstance(val, (int, float)):
                    metric_values[metric_name].append(float(val))

        aggregated = {}
        for metric_name, values in sorted(metric_values.items()):
            if not values:
                continue
            aggregated[metric_name] = {
                "min": round(min(values), 4),
                "max": round(max(values), 4),
                "avg": round(sum(values) / len(values), 4),
                "samples": len(values),
            }

        summaries[month_key] = {
            "period": month_key,
            "entry_count": len(month_entries),
            "metrics": aggregated,
            "generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        }
    return summaries


def main() -> None:
    parser = argparse.ArgumentParser(description="Rotate heartbeat history")
    parser.add_argument(
        "--execute", action="store_true",
        help="Actually rotate (default: dry-run)",
    )
    parser.add_argument(
        "--dry-run", action="store_true",
        help="Show what would happen (default behavior)",
    )
    parser.add_argument(
        "--days", type=int, default=None,
        help="Override retention days (default: from config or 30)",
    )
    parser.add_argument(
        "--config", type=str, default=None,
        help="Path to heartbeat config file",
    )
    args = parser.parse_args()

    config_path = Path(args.config) if args.config else DEFAULT_CONFIG
    retention_days = args.days if args.days is not None else load_retention_days(config_path)

    now = datetime.now(timezone.utc)
    cutoff = now - timedelta(days=retention_days)

    entries = parse_entries(HISTORY_FILE)
    if not entries:
        print("No heartbeat history entries found.", file=sys.stderr)
        return

    recent, old = partition_entries(entries, cutoff)

    mode = "EXECUTING" if args.execute else "DRY RUN"
    print("Heartbeat rotation (%s)" % mode, file=sys.stderr)
    print("  History file: %s" % HISTORY_FILE, file=sys.stderr)
    print("  Retention: %d days (cutoff: %s)" % (retention_days, cutoff.strftime("%Y-%m-%d")), file=sys.stderr)
    print("  Total entries: %d" % len(entries), file=sys.stderr)
    print("  Recent (keep raw): %d" % len(recent), file=sys.stderr)
    print("  Old (summarize): %d" % len(old), file=sys.stderr)

    if not old:
        print("  Nothing to rotate -- all entries within retention window.", file=sys.stderr)
        return

    summaries = aggregate_monthly(old)

    for month_key, summary in sorted(summaries.items()):
        summary_path = MONTHLY_DIR / ("%s.json" % month_key)
        metric_count = len(summary.get("metrics", {}))
        if args.execute:
            MONTHLY_DIR.mkdir(parents=True, exist_ok=True)
            # Merge with existing summary if present
            if summary_path.exists():
                try:
                    existing = json.loads(summary_path.read_text(encoding="utf-8"))
                    existing_count = existing.get("entry_count", 0)
                    summary["entry_count"] += existing_count
                    # Merge metrics: combine samples
                    for mk, mv in existing.get("metrics", {}).items():
                        if mk in summary["metrics"]:
                            s = summary["metrics"][mk]
                            s["min"] = min(s["min"], mv.get("min", s["min"]))
                            s["max"] = max(s["max"], mv.get("max", s["max"]))
                            total_samples = s["samples"] + mv.get("samples", 0)
                            if total_samples > 0:
                                s["avg"] = round(
                                    (s["avg"] * s["samples"] + mv.get("avg", 0) * mv.get("samples", 0)) / total_samples,
                                    4,
                                )
                                s["samples"] = total_samples
                        else:
                            summary["metrics"][mk] = mv
                except (json.JSONDecodeError, OSError):
                    pass
            summary_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")
            print("  WROTE: %s (%d entries, %d metrics)" % (summary_path.name, summary["entry_count"], metric_count), file=sys.stderr)
        else:
            print("  WOULD WRITE: %s (%d entries, %d metrics)" % (month_key + ".json", summary["entry_count"], metric_count), file=sys.stderr)

    if args.execute:
        # Truncate history to recent entries only
        with HISTORY_FILE.open("w", encoding="utf-8") as f:
            for entry in recent:
                f.write(json.dumps(entry, separators=(",", ":")) + "\n")
        print("  TRUNCATED: %s to %d entries" % (HISTORY_FILE.name, len(recent)), file=sys.stderr)
    else:
        print("  WOULD TRUNCATE: %s from %d to %d entries" % (HISTORY_FILE.name, len(entries), len(recent)), file=sys.stderr)

    print("  Done.", file=sys.stderr)


if __name__ == "__main__":
    main()
