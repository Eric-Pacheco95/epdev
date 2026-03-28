#!/usr/bin/env python3
"""Event log rotation — stdlib only, no external deps.

Manages JSONL event file lifecycle:
  1. Monthly rollup: aggregate daily files into summary JSON
  2. Gzip archival: compress old JSONL files
  3. Retention: delete files beyond retention window

Usage:
    python tools/scripts/rotate_events.py                # dry-run (show what would happen)
    python tools/scripts/rotate_events.py --execute       # actually rotate
    python tools/scripts/rotate_events.py --config path   # custom config

Reads retention settings from heartbeat_config.json.
"""

from __future__ import annotations

import argparse
import gzip
import json
import sys
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_CONFIG = REPO_ROOT / "heartbeat_config.json"


def load_config(config_path: Path) -> dict:
    if not config_path.is_file():
        return {"retention": {"raw_days": 90, "rollup_after_days": 30, "gzip_after_days": 180}}
    try:
        cfg = json.loads(config_path.read_text(encoding="utf-8"))
        return cfg
    except (json.JSONDecodeError, OSError):
        return {"retention": {"raw_days": 90, "rollup_after_days": 30, "gzip_after_days": 180}}


def resolve_root(cfg: dict) -> Path:
    raw = cfg.get("root_dir", ".")
    p = Path(raw)
    return p if p.is_absolute() else REPO_ROOT / p


def get_event_files(events_dir: Path) -> list[tuple[Path, datetime]]:
    """Return list of (path, date) for JSONL event files."""
    results = []
    if not events_dir.is_dir():
        return results
    for p in sorted(events_dir.glob("*.jsonl")):
        try:
            d = datetime.strptime(p.stem, "%Y-%m-%d").replace(tzinfo=timezone.utc)
            results.append((p, d))
        except ValueError:
            continue
    return results


def rollup_month(events_dir: Path, year: int, month: int, files: list[Path],
                 execute: bool) -> Path | None:
    """Aggregate daily JSONL files into a monthly summary JSON."""
    rollup_dir = events_dir / "rollups"
    rollup_path = rollup_dir / f"{year}-{month:02d}_summary.json"

    if rollup_path.exists():
        return rollup_path

    # Aggregate metrics from JSONL records
    total_records = 0
    tools_counter: dict[str, int] = defaultdict(int)
    sessions = set()
    failures = 0

    for f in files:
        with f.open(encoding="utf-8") as fh:
            for line in fh:
                line = line.strip()
                if not line:
                    continue
                try:
                    rec = json.loads(line)
                    total_records += 1
                    tool = rec.get("tool", "")
                    if tool:
                        tools_counter[tool] += 1
                    sid = rec.get("session_id", "")
                    if sid:
                        sessions.add(sid)
                    if rec.get("success") is False:
                        failures += 1
                except (json.JSONDecodeError, KeyError):
                    continue

    summary = {
        "period": f"{year}-{month:02d}",
        "total_records": total_records,
        "unique_sessions": len(sessions),
        "total_failures": failures,
        "top_tools": sorted(tools_counter.items(), key=lambda x: -x[1])[:20],
        "files_aggregated": len(files),
        "generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
    }

    if execute:
        rollup_dir.mkdir(parents=True, exist_ok=True)
        rollup_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")
        print(f"  CREATED: {rollup_path.relative_to(events_dir.parent.parent)}")
    else:
        print(f"  WOULD CREATE: {rollup_path.name} ({total_records} records, {len(files)} files)")

    return rollup_path


def main() -> None:
    parser = argparse.ArgumentParser(description="Rotate event JSONL files")
    parser.add_argument("--execute", action="store_true", help="Actually perform rotation (default: dry-run)")
    parser.add_argument("--config", type=str, default=None, help="Path to config file")
    args = parser.parse_args()

    config_path = Path(args.config) if args.config else DEFAULT_CONFIG
    cfg = load_config(config_path)
    root_dir = resolve_root(cfg)
    events_dir = root_dir / "history" / "events"

    retention = cfg.get("retention", {})
    rollup_days = retention.get("rollup_after_days", 30)
    gzip_days = retention.get("gzip_after_days", 180)

    now = datetime.now(timezone.utc)
    rollup_cutoff = now - timedelta(days=rollup_days)
    gzip_cutoff = now - timedelta(days=gzip_days)

    files = get_event_files(events_dir)
    if not files:
        print("No event files found.")
        return

    mode = "EXECUTING" if args.execute else "DRY RUN"
    print(f"\nEvent rotation ({mode})")
    print(f"  Rollup after: {rollup_days} days")
    print(f"  Gzip after: {gzip_days} days")
    print(f"  Files found: {len(files)}")
    print()

    # Group files by month for rollup
    monthly: dict[tuple[int, int], list[Path]] = defaultdict(list)
    for path, date in files:
        if date < rollup_cutoff:
            monthly[(date.year, date.month)].append(path)

    # Rollup
    if monthly:
        print("Monthly rollups:")
        for (year, month), month_files in sorted(monthly.items()):
            rollup_month(events_dir, year, month, month_files, args.execute)

    # Gzip
    gzip_candidates = [(p, d) for p, d in files if d < gzip_cutoff and p.suffix == ".jsonl"]
    if gzip_candidates:
        print(f"\nGzip archival ({len(gzip_candidates)} files):")
        for path, date in gzip_candidates:
            gz_path = path.with_suffix(".jsonl.gz")
            if gz_path.exists():
                continue
            if args.execute:
                with path.open("rb") as f_in:
                    with gzip.open(gz_path, "wb") as f_out:
                        f_out.writelines(f_in)
                path.unlink()
                print(f"  COMPRESSED: {path.name} -> {gz_path.name}")
            else:
                print(f"  WOULD COMPRESS: {path.name}")

    if not monthly and not gzip_candidates:
        print("Nothing to rotate -- all files within retention window.")

    print()


if __name__ == "__main__":
    main()
