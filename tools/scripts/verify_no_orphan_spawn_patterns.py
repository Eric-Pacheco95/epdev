#!/usr/bin/env python3
"""Anti-criterion verifier for orphan-prevention-oom PRD-1.

Exits 1 (with diagnostic output) if ANY of the three forbidden spawn patterns
reappears anywhere in the three surface areas. Greps explicit pattern list -- no
filter-and-print, no "informational only" mode. Any match is a rollback trigger.

Surface 1 (isc_executor.py): no `shell=True`
Surface 2 (.bat wrappers): no `for /f ... python|powershell|today.py`
Surface 3 (three .py callers): no `subprocess.run([claude` or `subprocess.Popen([claude`

Usage:
    python tools/scripts/verify_no_orphan_spawn_patterns.py
    python tools/scripts/verify_no_orphan_spawn_patterns.py --json
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]

# Surface 1: isc_executor.py must not contain literal shell-enable kwarg
_ISC_EXECUTOR = REPO_ROOT / "tools" / "scripts" / "isc_executor.py"
_SHELL_TRUE_NEEDLE = "shell" + "=" + "True"  # constructed to avoid self-match

# Surface 2: .bat wrappers -- subprocess-based date source patterns
_BAT_DIR = REPO_ROOT / "tools" / "scripts"
_BAT_FORBIDDEN_RE = re.compile(
    r"for\s+/f\s+.*\bin\s*\(\s*['\"]?.*?(python(\.exe)?|powershell|pwsh|today\.py)\b",
    re.IGNORECASE,
)

# Surface 3: three .py callers -- raw subprocess spawning claude
_PY_TARGETS = [
    REPO_ROOT / "tools" / "scripts" / "overnight_runner.py",
    REPO_ROOT / "tools" / "scripts" / "jarvis_dispatcher.py",
    REPO_ROOT / "tools" / "scripts" / "self_diagnose_wrapper.py",
]
_CLAUDE_CALL_RE = re.compile(
    r"subprocess\.(run|Popen)\(\s*\[\s*['\"]?(claude|CLAUDE_BIN)",
    re.IGNORECASE,
)


def audit_isc_executor() -> dict:
    if not _ISC_EXECUTOR.exists():
        return {"surface": "isc_executor.py", "status": "error", "reason": "file missing"}
    src = _ISC_EXECUTOR.read_text(encoding="utf-8")
    hits: list[str] = []
    for i, line in enumerate(src.splitlines(), start=1):
        if _SHELL_TRUE_NEEDLE in line:
            hits.append(f"L{i}: {line.strip()}")
    return {
        "surface": "isc_executor.py",
        "status": "fail" if hits else "pass",
        "hits": hits,
    }


def audit_bat_wrappers() -> dict:
    all_hits: list[dict] = []
    for bat in sorted(_BAT_DIR.glob("run_*.bat")):
        try:
            src = bat.read_text(encoding="utf-8", errors="replace")
        except Exception as exc:
            all_hits.append({"file": str(bat.relative_to(REPO_ROOT)),
                             "hit": f"read error: {exc}"})
            continue
        for i, line in enumerate(src.splitlines(), start=1):
            if _BAT_FORBIDDEN_RE.search(line):
                all_hits.append({
                    "file": str(bat.relative_to(REPO_ROOT)),
                    "hit": f"L{i}: {line.strip()}",
                })
    return {
        "surface": ".bat wrappers",
        "status": "fail" if all_hits else "pass",
        "hits": all_hits,
    }


def audit_py_callers() -> dict:
    all_hits: list[dict] = []
    for py in _PY_TARGETS:
        if not py.exists():
            all_hits.append({"file": str(py.relative_to(REPO_ROOT)), "hit": "file missing"})
            continue
        src = py.read_text(encoding="utf-8")
        for i, line in enumerate(src.splitlines(), start=1):
            if _CLAUDE_CALL_RE.search(line):
                all_hits.append({
                    "file": str(py.relative_to(REPO_ROOT)),
                    "hit": f"L{i}: {line.strip()}",
                })
    return {
        "surface": "three .py callers",
        "status": "fail" if all_hits else "pass",
        "hits": all_hits,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--json", action="store_true", help="Emit JSON output")
    args = parser.parse_args()

    results = [audit_isc_executor(), audit_bat_wrappers(), audit_py_callers()]
    any_fail = any(r["status"] != "pass" for r in results)
    exit_code = 1 if any_fail else 0

    if args.json:
        print(json.dumps({
            "surfaces": results,
            "any_fail": any_fail,
            "exit_code": exit_code,
        }, indent=2))
    else:
        for r in results:
            marker = {"pass": "OK", "fail": "FAIL", "error": "ERR"}.get(r["status"], "?")
            print(f"[{marker}] {r['surface']}")
            for h in r.get("hits", []):
                if isinstance(h, dict):
                    print(f"       {h.get('file', '?')}: {h.get('hit', '')}")
                else:
                    print(f"       {h}")
        print()
        print(f"Result: {'FAIL' if any_fail else 'PASS'}")

    return exit_code


if __name__ == "__main__":
    sys.exit(main())
