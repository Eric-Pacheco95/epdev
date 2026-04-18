#!/usr/bin/env python3
"""Verify that every `.bat` wrapper under tools/scripts/ resolves its log date
via a native Windows token (`%DATE%` or `%DATE:~...%` substring extraction) and
does not spawn any helper process to get today's date.

Exits 0 if all wrappers pass, 1 if any wrapper sources its date from a
subprocess (the architectural pattern that leaked orphaned python.exe at 2026-04-18).

Usage:
    python tools/scripts/verify_bat_date_tokens.py           # exit non-zero on violations
    python tools/scripts/verify_bat_date_tokens.py --json    # machine-readable output
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPTS_DIR = REPO_ROOT / "tools" / "scripts"

# Any `for /f ... in ('...python...today.py...')` or `for /f ... in ('powershell...Get-Date...')`
# inside a .bat file is a subprocess-date-source. We only flag .bat files that ALSO write to
# a dated log (LOGDATE + LOGFILE pattern); wrappers that don't use a date token are irrelevant.
_SUBPROC_DATE_RE = re.compile(
    r"for\s+/f\s+.*\bin\s*\(\s*['\"]?.*?(python(\.exe)?|powershell|pwsh|today\.py)\b",
    re.IGNORECASE,
)
_LOGDATE_RE = re.compile(r"\bset\s+LOGDATE\s*=", re.IGNORECASE)


def audit_bat(path: Path) -> dict:
    """Return audit record for a single .bat file."""
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except Exception as exc:
        return {
            "file": str(path.relative_to(REPO_ROOT)),
            "status": "error",
            "reason": f"read error: {exc}",
        }

    uses_logdate = bool(_LOGDATE_RE.search(text))
    subproc_hits: list[str] = []
    for i, line in enumerate(text.splitlines(), start=1):
        if _SUBPROC_DATE_RE.search(line):
            subproc_hits.append(f"L{i}: {line.strip()}")

    if not uses_logdate:
        return {
            "file": str(path.relative_to(REPO_ROOT)),
            "status": "skip",
            "reason": "no LOGDATE variable; not a log-writing wrapper",
        }

    if subproc_hits:
        return {
            "file": str(path.relative_to(REPO_ROOT)),
            "status": "fail",
            "reason": "date sourced via subprocess",
            "hits": subproc_hits,
        }

    return {
        "file": str(path.relative_to(REPO_ROOT)),
        "status": "pass",
        "reason": "native date token",
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--json", action="store_true", help="Emit JSON output")
    args = parser.parse_args()

    bat_files = sorted(SCRIPTS_DIR.glob("run_*.bat"))
    results = [audit_bat(p) for p in bat_files]

    fails = [r for r in results if r["status"] == "fail"]
    errors = [r for r in results if r["status"] == "error"]
    exit_code = 1 if (fails or errors) else 0

    if args.json:
        print(json.dumps({
            "bat_count": len(bat_files),
            "pass": sum(1 for r in results if r["status"] == "pass"),
            "fail": len(fails),
            "skip": sum(1 for r in results if r["status"] == "skip"),
            "error": len(errors),
            "results": results,
            "exit_code": exit_code,
        }, indent=2))
    else:
        for r in results:
            marker = {"pass": "OK", "fail": "FAIL", "skip": "--", "error": "ERR"}[r["status"]]
            print(f"[{marker}] {r['file']}: {r['reason']}")
            for h in r.get("hits", []):
                print(f"       {h}")
        print()
        print(f"Summary: {len(results)} .bat files | "
              f"{sum(1 for r in results if r['status']=='pass')} pass, "
              f"{len(fails)} fail, "
              f"{sum(1 for r in results if r['status']=='skip')} skip, "
              f"{len(errors)} error")

    return exit_code


if __name__ == "__main__":
    sys.exit(main())
