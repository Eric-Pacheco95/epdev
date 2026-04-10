"""
migrate_lineage.py - One-time migration of signal_lineage.jsonl from old schema to new schema.

Old schema (one line per signal):
  {"signal_filename": "memory/learning/signals/processed/foo.md", "synthesis_filename": "2026-03-27_synthesis_5.md", "date": "2026-03-27"}

New schema (one line per synthesis run):
  {"timestamp": "2026-04-09T00:00:00Z", "synthesis_id": "2026-04-09_synthesis", "signal_count": 4, "signals": ["foo.md", "bar.md"]}

Usage:
  python tools/scripts/migrate_lineage.py             # execute migration
  python tools/scripts/migrate_lineage.py --dry-run   # preview changes only
  python tools/scripts/migrate_lineage.py --validate  # validate existing file, no write
"""

import argparse
import json
import sys
from collections import OrderedDict
from pathlib import Path

LINEAGE_PATH = Path(__file__).parent.parent.parent / "data" / "signal_lineage.jsonl"

# Prefixes to strip from signal filenames
SIGNAL_PREFIXES = [
    "memory/learning/signals/processed/",
    "memory\\learning\\signals\\processed\\",
    "memory/learning/signals/",
    "memory\\learning\\signals\\",
]


def strip_signal_prefix(filename: str) -> str:
    """Strip known path prefixes, return bare filename."""
    # Normalize backslashes to forward slashes
    normalized = filename.replace("\\", "/")
    for prefix in SIGNAL_PREFIXES:
        prefix_norm = prefix.replace("\\", "/")
        if normalized.startswith(prefix_norm):
            return normalized[len(prefix_norm):]
    # If it's already just a filename, return as-is
    return normalized.split("/")[-1] if "/" in normalized else normalized


def is_old_schema(record: dict) -> bool:
    return "signal_filename" in record


def is_new_schema(record: dict) -> bool:
    return "synthesis_id" in record and "signals" in record


def migrate(lines: list[str]) -> list[dict]:
    """
    Parse all lines, convert old-schema records by grouping on synthesis_filename,
    and return a list of new-schema records (old groups first, then existing new-schema records).

    Idempotent: if all records are already new-schema, they pass through unchanged
    (with signal filenames normalized).
    """
    old_groups: OrderedDict[str, dict] = OrderedDict()  # synthesis_filename -> {date, signals}
    new_records: list[dict] = []
    errors: list[str] = []

    for i, line in enumerate(lines, 1):
        line = line.strip()
        if not line:
            continue
        try:
            record = json.loads(line)
        except json.JSONDecodeError as e:
            errors.append(f"Line {i}: JSON parse error: {e}")
            continue

        if is_old_schema(record):
            syn = record.get("synthesis_filename", "unknown")
            date = record.get("date", "1970-01-01")
            sig = strip_signal_prefix(record.get("signal_filename", ""))
            if syn not in old_groups:
                old_groups[syn] = {"date": date, "signals": []}
            old_groups[syn]["signals"].append(sig)
        elif is_new_schema(record):
            # Normalize signal paths in existing new-schema records
            normalized_signals = [strip_signal_prefix(s) for s in record.get("signals", [])]
            record["signals"] = normalized_signals
            new_records.append(record)
        else:
            errors.append(f"Line {i}: Unrecognized schema: {record}")

    if errors:
        for err in errors:
            print(f"ERROR: {err}")
        sys.exit(1)

    # Convert old groups to new schema
    converted: list[dict] = []
    for syn_filename, group in old_groups.items():
        # synthesis_id: strip .md extension if present
        syn_id = syn_filename
        if syn_id.endswith(".md"):
            syn_id = syn_id[:-3]
        date = group["date"]
        timestamp = f"{date}T00:00:00Z"
        converted.append({
            "timestamp": timestamp,
            "synthesis_id": syn_id,
            "signal_count": len(group["signals"]),
            "signals": group["signals"],
        })

    return converted + new_records


def validate_file(path: Path) -> tuple[int, list[str]]:
    """Read and validate all records. Returns (count, errors)."""
    errors = []
    count = 0
    if not path.exists():
        return 0, [f"File not found: {path}"]
    with open(path, "r", encoding="utf-8") as f:
        for i, line in enumerate(f, 1):
            line = line.strip()
            if not line:
                continue
            try:
                record = json.loads(line)
                count += 1
                if not is_new_schema(record):
                    errors.append(f"Line {i}: Still old schema or unknown: {list(record.keys())}")
                # Check no path prefixes remain in signals
                for sig in record.get("signals", []):
                    for prefix in ["memory/", "memory\\"]:
                        if sig.startswith(prefix):
                            errors.append(f"Line {i}: Signal still has path prefix: {sig}")
            except json.JSONDecodeError as e:
                errors.append(f"Line {i}: JSON parse error: {e}")
    return count, errors


def main():
    parser = argparse.ArgumentParser(description="Migrate signal_lineage.jsonl to unified schema")
    parser.add_argument("--dry-run", action="store_true", help="Print what would change without writing")
    parser.add_argument("--validate", action="store_true", help="Validate existing file only, no write")
    args = parser.parse_args()

    if not LINEAGE_PATH.exists():
        print(f"ERROR: {LINEAGE_PATH} not found")
        sys.exit(1)

    if args.validate:
        count, errors = validate_file(LINEAGE_PATH)
        if errors:
            for err in errors:
                print(f"FAIL: {err}")
            print(f"Validation FAILED: {len(errors)} error(s) in {count} records")
            sys.exit(1)
        else:
            print(f"OK: {count} records, all new schema, no path prefixes")
        return

    # Read original lines
    with open(LINEAGE_PATH, "r", encoding="utf-8") as f:
        lines = f.readlines()

    original_count = sum(1 for l in lines if l.strip())
    print(f"Input:  {original_count} non-empty lines")

    # Count old vs new in original
    old_count = sum(1 for l in lines if l.strip() and "signal_filename" in l)
    new_count = original_count - old_count
    print(f"  Old schema: {old_count} lines")
    print(f"  New schema: {new_count} lines")

    records = migrate(lines)
    output_count = len(records)
    print(f"Output: {output_count} records (old {old_count} lines -> grouped by synthesis)")

    if args.dry_run:
        print("\n-- DRY RUN: first 5 output records --")
        for r in records[:5]:
            print(json.dumps(r))
        if output_count > 5:
            print(f"  ... ({output_count - 5} more)")
        print("\nNo file written (--dry-run)")
        return

    # Write output
    with open(LINEAGE_PATH, "w", encoding="utf-8", newline="\n") as f:
        for record in records:
            f.write(json.dumps(record) + "\n")

    print(f"Written: {LINEAGE_PATH}")

    # Validate immediately
    count, errors = validate_file(LINEAGE_PATH)
    if errors:
        for err in errors:
            print(f"FAIL: {err}")
        print(f"Post-write validation FAILED: {len(errors)} error(s)")
        sys.exit(1)
    else:
        print(f"Validated: {count} records OK")

    # Check for forbidden strings
    content = LINEAGE_PATH.read_text(encoding="utf-8")
    checks = [
        ("signal_filename", "old-schema key"),
        ("processed/", "processed/ path prefix"),
        ("processed\\", "processed\\ path prefix"),
    ]
    any_fail = False
    for needle, label in checks:
        if needle in content:
            print(f"FAIL: '{needle}' ({label}) still present in output")
            any_fail = True
        else:
            print(f"OK: no '{needle}' in output")

    if any_fail:
        sys.exit(1)


if __name__ == "__main__":
    main()
