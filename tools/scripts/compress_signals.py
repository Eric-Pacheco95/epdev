#!/usr/bin/env python3
"""Signal compression -- gzip processed signals older than 180 days.

Prevents unbounded growth from autonomous signal producers.
Scans memory/learning/signals/processed/ for .md files older than
the configured threshold and gzips them in-place.

Usage:
    python tools/scripts/compress_signals.py              # dry-run
    python tools/scripts/compress_signals.py --execute    # actually compress
    python tools/scripts/compress_signals.py --days 90    # custom age threshold

Reads gzip_after_days from heartbeat_config.json retention section.
"""

from __future__ import annotations

import argparse
import gzip
import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_CONFIG = REPO_ROOT / "heartbeat_config.json"
DEFAULT_SIGNAL_DIR = REPO_ROOT / "memory" / "learning" / "signals" / "processed"


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


def main() -> None:
    parser = argparse.ArgumentParser(description="Compress old processed signals")
    parser.add_argument(
        "--execute", action="store_true",
        help="Actually compress files (default: dry-run)",
    )
    # Keep --dry-run as explicit alias (no-op since dry-run is default)
    parser.add_argument(
        "--dry-run", action="store_true",
        help="Show what would happen without changes (default behavior)",
    )
    parser.add_argument(
        "--days", type=int, default=None,
        help="Override age threshold in days (default: from config or 180)",
    )
    parser.add_argument(
        "--config", type=str, default=None,
        help="Path to heartbeat config file",
    )
    args = parser.parse_args()

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
