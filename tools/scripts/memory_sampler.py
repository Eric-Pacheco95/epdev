#!/usr/bin/env python3
"""Per-tick sum-commit memory sampler.

Appends one JSONL line to `data/logs/memory_timeseries.jsonl` per invocation.
Fields: ts (ISO-8601 UTC), commit_bytes_sum, pagefile_free_gb, ram_free_gb,
top5_procs (list of {name, pid, paged_mb} ordered by PagedMemorySize desc).

PowerShell Get-Process only for process-level sum and top-5; psutil for
pagefile/RAM free (both non-hanging under memory pressure per incident-triage
rules R2/R3 -- Windows API classes and performance-counter cmdlets are
explicitly avoided because they hang under the exact pressure this telemetry
is meant to catch).

Registered via register_memory_sampler_tasks.ps1 as two Task Scheduler tasks:
  Jarvis-MemorySampler-Night  every 2 min, active 22:00-08:00
  Jarvis-MemorySampler-Day    every 10 min, active 08:00-22:00

Usage:
    python tools/scripts/memory_sampler.py
"""

from __future__ import annotations

import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path

import psutil

REPO_ROOT = Path(__file__).resolve().parents[2]
LOG_FILE = REPO_ROOT / "data" / "logs" / "memory_timeseries.jsonl"

PS_CMD = (
    "$p = Get-Process; "
    "$sum = ($p | Measure-Object PagedMemorySize -Sum).Sum; "
    "$top = $p | Sort-Object PagedMemorySize -Descending | Select-Object -First 5 "
    "| ForEach-Object { [pscustomobject]@{ name = $_.ProcessName; pid = $_.Id; "
    "paged_mb = [math]::Round($_.PagedMemorySize / 1MB, 1) } }; "
    "ConvertTo-Json -Compress -InputObject @{ sum = $sum; top5 = @($top) }"
)


def collect_from_powershell() -> dict:
    result = subprocess.run(
        ["powershell", "-NoProfile", "-NonInteractive", "-Command", PS_CMD],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=30,
        check=True,
    )
    stdout = result.stdout.strip()
    if not stdout:
        raise RuntimeError("PowerShell returned empty stdout")
    return json.loads(stdout)


def build_entry() -> dict:
    ps_data = collect_from_powershell()
    swap = psutil.swap_memory()
    vm = psutil.virtual_memory()

    top5_raw = ps_data.get("top5") or []
    if isinstance(top5_raw, dict):
        top5_raw = [top5_raw]

    return {
        "ts": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "commit_bytes_sum": int(ps_data["sum"]),
        "pagefile_free_gb": round(swap.free / (1024 ** 3), 3),
        "ram_free_gb": round(vm.available / (1024 ** 3), 3),
        "top5_procs": [
            {
                "name": str(p["name"]),
                "pid": int(p["pid"]),
                "paged_mb": float(p["paged_mb"]),
            }
            for p in top5_raw
        ],
    }


def main() -> int:
    entry = build_entry()
    LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
    with LOG_FILE.open("a", encoding="utf-8") as f:
        f.write(json.dumps(entry) + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
