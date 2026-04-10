#!/usr/bin/env python3
"""Signal management -- compression, grouping, and lineage tracking.

Multi-mode CLI for /synthesize-signals and /learning-capture skills.

Usage:
    python tools/scripts/compress_signals.py                       # dry-run compression
    python tools/scripts/compress_signals.py --execute             # actually compress
    python tools/scripts/compress_signals.py --days 90             # custom age threshold
    python tools/scripts/compress_signals.py --group               # group unprocessed signals by category
    python tools/scripts/compress_signals.py --group --json        # JSON output for LLM consumption
    python tools/scripts/compress_signals.py --stats               # signal counts and velocity
    python tools/scripts/compress_signals.py --move                # move signals to processed/
    python tools/scripts/compress_signals.py --lineage SYNTHESIS   # update lineage for a synthesis run

Reads gzip_after_days from heartbeat_config.json retention section.
"""

from __future__ import annotations

import argparse
import gzip
import json
import os
import re
import sys
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_CONFIG = REPO_ROOT / "heartbeat_config.json"
SIGNALS_DIR = REPO_ROOT / "memory" / "learning" / "signals"
# Legacy alias — compression still scans the signals dir for old .md.gz files
DEFAULT_SIGNAL_DIR = SIGNALS_DIR
UNPROCESSED_DIR = SIGNALS_DIR
FAILURES_DIR = REPO_ROOT / "memory" / "learning" / "failures"
ABSORBED_DIR = REPO_ROOT / "memory" / "learning" / "absorbed"
LINEAGE_FILE = REPO_ROOT / "data" / "signal_lineage.jsonl"
SIGNAL_META = REPO_ROOT / "memory" / "learning" / "_signal_meta.json"


def load_synthesized_signals() -> set[str]:
    """Read lineage JSONL and return set of all signal filenames that have been synthesized.

    Handles both old schema (signal_filename per line) and new schema (signals array per line).
    Returns bare filenames (no path prefix).
    """
    synthesized = set()
    if not LINEAGE_FILE.is_file():
        return synthesized
    try:
        for line in LINEAGE_FILE.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                record = json.loads(line)
            except json.JSONDecodeError:
                continue
            # New schema: {"signals": ["file1.md", ...]}
            if "signals" in record:
                for s in record["signals"]:
                    synthesized.add(Path(s).name)
            # Old schema: {"signal_filename": "memory/learning/signals/processed/file.md"}
            elif "signal_filename" in record:
                synthesized.add(Path(record["signal_filename"]).name)
    except OSError:
        pass
    return synthesized


def get_last_synthesis_timestamp() -> datetime | None:
    """Return the timestamp of the most recent synthesis run from lineage, or None."""
    if not LINEAGE_FILE.is_file():
        return None
    latest = None
    try:
        for line in LINEAGE_FILE.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                record = json.loads(line)
            except json.JSONDecodeError:
                continue
            ts_str = record.get("timestamp") or record.get("date")
            if not ts_str:
                continue
            try:
                if "T" in ts_str:
                    ts = datetime.fromisoformat(ts_str.replace("Z", "+00:00"))
                else:
                    ts = datetime.strptime(ts_str, "%Y-%m-%d").replace(tzinfo=timezone.utc)
                if latest is None or ts > latest:
                    latest = ts
            except (ValueError, TypeError):
                continue
    except OSError:
        pass
    return latest


def _lock_file(fh):
    """Acquire an exclusive lock on a file handle. Cross-platform."""
    if os.name == "nt":
        import msvcrt
        msvcrt.locking(fh.fileno(), msvcrt.LK_LOCK, 1)
    else:
        import fcntl
        fcntl.flock(fh, fcntl.LOCK_EX)


def _unlock_file(fh):
    """Release a file lock. Cross-platform."""
    if os.name == "nt":
        import msvcrt
        msvcrt.locking(fh.fileno(), msvcrt.LK_UNLCK, 1)
    else:
        import fcntl
        fcntl.flock(fh, fcntl.LOCK_UN)


def _count_synthesis_runs() -> int:
    """Count number of synthesis runs recorded in lineage."""
    if not LINEAGE_FILE.is_file():
        return 0
    count = 0
    for line in LINEAGE_FILE.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            json.loads(line)
            count += 1
        except json.JSONDecodeError:
            continue
    return count


def validate_lineage_integrity() -> tuple[int, int]:
    """Validate JSONL integrity. Returns (valid_count, error_count)."""
    if not LINEAGE_FILE.is_file():
        return 0, 0
    valid = 0
    errors = 0
    for line in LINEAGE_FILE.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            json.loads(line)
            valid += 1
        except json.JSONDecodeError:
            errors += 1
    return valid, errors


def load_gzip_days(config_path: Path) -> int:
    """Read gzip_after_days from heartbeat config, default 180."""
    if config_path.is_file():
        try:
            cfg = json.loads(config_path.read_text(encoding="utf-8"))
            return cfg.get("retention", {}).get("gzip_after_days", 180)
        except (json.JSONDecodeError, OSError):
            pass
    return 180


def find_compressible(signal_dir: Path, max_age_days: int) -> list[Path]:
    """Return .md files older than max_age_days by mtime."""
    if not signal_dir.is_dir():
        return []
    cutoff = datetime.now(timezone.utc) - timedelta(days=max_age_days)
    results = []
    for p in sorted(signal_dir.glob("*.md")):
        if not p.is_file():
            continue
        mtime = datetime.fromtimestamp(p.stat().st_mtime, tz=timezone.utc)
        if mtime < cutoff:
            results.append(p)
    return results


def compress_file(path: Path) -> Path:
    """Gzip a file in-place: file.md -> file.md.gz. Returns gz path."""
    gz_path = path.with_suffix(path.suffix + ".gz")
    with path.open("rb") as f_in:
        with gzip.open(gz_path, "wb") as f_out:
            f_out.writelines(f_in)
    path.unlink()
    return gz_path


def _sanitize_ascii(text: str) -> str:
    """Replace common Unicode chars with ASCII for Windows cp1252."""
    replacements = {
        "\u2192": "->", "\u2014": "--", "\u2013": "-",
        "\u2018": "'", "\u2019": "'", "\u201c": '"', "\u201d": '"',
    }
    for uni, asc in replacements.items():
        text = text.replace(uni, asc)
    return text


def parse_signal_frontmatter(filepath: Path) -> dict:
    """Extract YAML-like frontmatter from a signal .md file."""
    try:
        text = filepath.read_text(encoding="utf-8")
    except Exception:
        return {"file": filepath.name, "error": "unreadable"}

    meta = {"file": filepath.name, "path": str(filepath)}

    # Parse frontmatter between --- delimiters
    fm_match = re.match(r"^---\s*\n(.*?)\n---", text, re.DOTALL)
    if fm_match:
        for line in fm_match.group(1).splitlines():
            kv = line.split(":", 1)
            if len(kv) == 2:
                key = kv[0].strip().lower()
                val = kv[1].strip()
                meta[key] = val

    # Extract rating if present
    rating_match = re.search(r"[Rr]ating:\s*(\d+)", text)
    if rating_match:
        meta["rating"] = int(rating_match.group(1))

    # Extract category from frontmatter or filename
    if "category" not in meta:
        # Infer from filename patterns
        name_lower = filepath.stem.lower()
        if "failure" in name_lower or "fail" in name_lower:
            meta["category"] = "failure"
        elif "pattern" in name_lower:
            meta["category"] = "pattern"
        elif "insight" in name_lower:
            meta["category"] = "insight"
        elif "anomaly" in name_lower:
            meta["category"] = "anomaly"
        elif "improvement" in name_lower:
            meta["category"] = "improvement"
        else:
            meta["category"] = "uncategorized"

    return meta


def group_signals() -> dict:
    """Group unprocessed signals by category with counts.

    Uses lineage JSONL to determine which signals have been synthesized.
    Only groups signals NOT referenced in lineage.
    """
    if not UNPROCESSED_DIR.is_dir():
        return {"groups": {}, "total": 0, "error": "signals directory not found"}

    synthesized = load_synthesized_signals()

    signals = []
    for f in sorted(UNPROCESSED_DIR.glob("*.md")):
        if f.name.startswith("_"):  # skip meta files
            continue
        if f.name in synthesized:
            continue  # already synthesized per lineage
        signals.append(parse_signal_frontmatter(f))

    # Group by category
    groups = defaultdict(list)
    for s in signals:
        cat = s.get("category", "uncategorized")
        groups[cat].append(s)

    # Also count failures (skip _ prefixed meta files)
    failure_count = 0
    if FAILURES_DIR.is_dir():
        failure_count = len([f for f in FAILURES_DIR.glob("*.md") if not f.name.startswith("_")])

    # Count absorbed content (skip _ prefixed meta files)
    absorbed_count = 0
    if ABSORBED_DIR.is_dir():
        absorbed_count = len([f for f in ABSORBED_DIR.glob("*.md") if not f.name.startswith("_")])

    return {
        "groups": {k: {"count": len(v), "signals": v} for k, v in sorted(groups.items())},
        "total_unprocessed": len(signals),
        "total_failures": failure_count,
        "total_absorbed": absorbed_count,
        "total_combined": len(signals) + failure_count + absorbed_count,
        "categories": {k: len(v) for k, v in sorted(groups.items())},
    }


def get_signal_stats() -> dict:
    """Compute signal counts, velocity, and metadata.

    Uses lineage JSONL to distinguish synthesized vs unprocessed signals.
    All signals live in signals/ (warehouse model — no processed/ directory).
    """
    all_signals = list(UNPROCESSED_DIR.glob("*.md")) if UNPROCESSED_DIR.is_dir() else []
    all_signals = [f for f in all_signals if not f.name.startswith("_")]
    compressed = list(UNPROCESSED_DIR.glob("*.md.gz")) if UNPROCESSED_DIR.is_dir() else []
    failures = list(FAILURES_DIR.glob("*.md")) if FAILURES_DIR.is_dir() else []
    absorbed = list(ABSORBED_DIR.glob("*.md")) if ABSORBED_DIR.is_dir() else []

    # Use lineage to determine synthesized vs unprocessed
    synthesized = load_synthesized_signals()
    unprocessed = [f for f in all_signals if f.name not in synthesized]
    processed = [f for f in all_signals if f.name in synthesized]

    # Signal velocity: count signals from last 7 days
    now = datetime.now(timezone.utc)
    week_ago = now - timedelta(days=7)
    recent = 0
    for f in all_signals:
        mtime = datetime.fromtimestamp(f.stat().st_mtime, tz=timezone.utc)
        if mtime > week_ago:
            recent += 1

    velocity = round(recent / 7, 2)

    # Last synthesis from lineage
    last_synth_ts = get_last_synthesis_timestamp()
    last_synth_str = last_synth_ts.strftime("%Y-%m-%dT%H:%M:%SZ") if last_synth_ts else None

    return {
        "unprocessed": len(unprocessed),
        "processed": len(processed),
        "compressed": len(compressed),
        "failures": len(failures),
        "absorbed": len(absorbed),
        "total_combined_unprocessed": len(unprocessed) + len(failures) + len(absorbed),
        "total_all_time": len(all_signals) + len(compressed),
        "velocity_per_day": velocity,
        "recent_7d": recent,
        "synthesis_runs": _count_synthesis_runs(),
        "synthesized_signals": len(synthesized),
        "last_synthesis": last_synth_str,
    }


def move_to_processed(signal_files: list[str] | None = None) -> dict:
    """DEPRECATED: Warehouse model — signals stay in signals/ permanently.

    Lineage JSONL tracks what has been synthesized. Use --lineage instead.
    """
    print("DEPRECATED: --move is no longer supported. Signals stay in signals/ permanently.", file=sys.stderr)
    print("Use --lineage to record which signals were consumed by synthesis.", file=sys.stderr)
    return {"moved": [], "count": 0, "errors": ["--move is deprecated (warehouse model)"]}


def update_lineage(synthesis_id: str, signal_files: list[str] | None = None) -> dict:
    """Append lineage record linking signals to a synthesis run.

    Uses file locking to prevent concurrent-write corruption.
    Only records unprocessed signals (not already in lineage).
    """
    LINEAGE_FILE.parent.mkdir(parents=True, exist_ok=True)

    # Validate existing JSONL integrity before appending
    valid, errors = validate_lineage_integrity()
    if errors > 0:
        print(f"WARNING: {errors} corrupted lines found in lineage JSONL", file=sys.stderr)

    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    # Gather unprocessed signal files if not provided
    if not signal_files:
        synthesized = load_synthesized_signals()
        signal_files = [
            f.name for f in UNPROCESSED_DIR.glob("*.md")
            if not f.name.startswith("_") and f.name not in synthesized
        ] if UNPROCESSED_DIR.is_dir() else []

    record = {
        "timestamp": now,
        "synthesis_id": synthesis_id,
        "signal_count": len(signal_files),
        "signals": signal_files,
    }

    line = json.dumps(record) + "\n"

    fh = open(LINEAGE_FILE, "a", encoding="utf-8")
    try:
        _lock_file(fh)
        fh.write(line)
        fh.flush()
    finally:
        try:
            _unlock_file(fh)
        except Exception:
            pass
        fh.close()

    return record


def main() -> None:
    parser = argparse.ArgumentParser(description="Signal management: compression, grouping, lineage")
    parser.add_argument("--execute", action="store_true", help="Actually compress files (default: dry-run)")
    parser.add_argument("--dry-run", action="store_true", help="Show what would happen (default)")
    parser.add_argument("--days", type=int, default=None, help="Age threshold in days (default: 180)")
    parser.add_argument("--config", type=str, default=None, help="Path to heartbeat config file")
    parser.add_argument("--group", action="store_true", help="Group unprocessed signals by category")
    parser.add_argument("--stats", action="store_true", help="Show signal counts and velocity")
    parser.add_argument("--move", action="store_true", help="Move unprocessed signals to processed/")
    parser.add_argument("--move-files", nargs="*", help="Specific files to move (default: all)")
    parser.add_argument("--lineage", type=str, metavar="SYNTHESIS_ID", help="Record lineage for a synthesis run")
    parser.add_argument("--json", action="store_true", help="JSON output")
    parser.add_argument("--pretty", action="store_true", help="Indent JSON")
    args = parser.parse_args()

    # Mode: stats
    if args.stats:
        stats = get_signal_stats()
        if args.json:
            indent = 2 if args.pretty else None
            print(json.dumps(stats, indent=indent))
        else:
            print(_sanitize_ascii(
                "Signals: %d unprocessed | %d processed | %d compressed | %d failures | %d absorbed"
                % (stats["unprocessed"], stats["processed"], stats["compressed"], stats["failures"], stats["absorbed"])
            ))
            print("  Combined unprocessed: %d (threshold: 35)" % stats["total_combined_unprocessed"])
            print("  Total all-time: %d" % stats["total_all_time"])
            print("  Velocity: %.2f/day (last 7d: %d)" % (stats["velocity_per_day"], stats["recent_7d"]))
            print("  Synthesis runs: %d | Synthesized signals: %d | Last: %s" % (
                stats["synthesis_runs"], stats["synthesized_signals"],
                stats["last_synthesis"] or "never"))
        return

    # Mode: group
    if args.group:
        grouped = group_signals()
        if args.json:
            indent = 2 if args.pretty else None
            print(json.dumps(grouped, indent=indent, default=str))
        else:
            print("Unprocessed signals: %d | Failures: %d" % (grouped["total_unprocessed"], grouped["total_failures"]))
            print("")
            for cat, count in grouped["categories"].items():
                print("  %s: %d signals" % (cat, count))
                for s in grouped["groups"][cat]["signals"]:
                    rating = s.get("rating", "?")
                    print("    [%s] %s" % (rating, s["file"]))
        return

    # Mode: move to processed
    if args.move:
        result = move_to_processed(args.move_files)
        if args.json:
            print(json.dumps(result, indent=2 if args.pretty else None))
        else:
            print("Moved %d signals to processed/" % result["count"])
            for f in result["moved"]:
                print("  -> %s" % f)
            for e in result["errors"]:
                print("  !! %s" % e)
        return

    # Mode: lineage
    if args.lineage:
        record = update_lineage(args.lineage, args.move_files)
        if args.json:
            print(json.dumps(record, indent=2 if args.pretty else None))
        else:
            print("Lineage recorded: %s -> %d signals" % (record["synthesis_id"], record["signal_count"]))
        return

    # Default mode: compression
    config_path = Path(args.config) if args.config else DEFAULT_CONFIG
    max_age = args.days if args.days is not None else load_gzip_days(config_path)

    candidates = find_compressible(DEFAULT_SIGNAL_DIR, max_age)

    mode = "EXECUTING" if args.execute else "DRY RUN"
    print("Signal compression (%s)" % mode, file=sys.stderr)
    print("  Directory: %s" % DEFAULT_SIGNAL_DIR, file=sys.stderr)
    print("  Age threshold: %d days" % max_age, file=sys.stderr)
    print("  Candidates: %d files" % len(candidates), file=sys.stderr)

    if not candidates:
        print("  Nothing to compress.", file=sys.stderr)
        return

    for path in candidates:
        if args.execute:
            gz_path = compress_file(path)
            print("  COMPRESSED: %s -> %s" % (path.name, gz_path.name), file=sys.stderr)
        else:
            size_kb = path.stat().st_size / 1024
            print("  WOULD COMPRESS: %s (%.1f KB)" % (path.name, size_kb), file=sys.stderr)

    print("  Done.", file=sys.stderr)


if __name__ == "__main__":
    main()
