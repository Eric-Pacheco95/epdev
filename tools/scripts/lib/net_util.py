#!/usr/bin/env python3
"""net_util -- shared network connection inspection helpers.

Uses PowerShell Get-NetTCPConnection for per-process attribution so callers
can report WHICH process is holding many connections, not just the count.
This avoids the "blame Claude" misattribution bug where a leaking dev server
on the same host triggered "close idle Claude sessions" alerts.

Zero external dependencies (stdlib + powershell.exe).
"""

from __future__ import annotations

import subprocess
from typing import NamedTuple


class Holder(NamedTuple):
    name: str        # process image name (e.g. "python", "claude")
    count: int       # number of established TCP connections owned by this PID
    cmd_hint: str    # truncated command line (e.g. "python -m uvicorn dashboard.app:app")


def get_https_summary(top_n: int = 3, timeout: int = 10) -> tuple[int | None, list[Holder]]:
    """Return (total_established_tcp_connections, top_n_holders).

    On failure (PowerShell missing, timeout, parse error) returns (None, []).
    Callers should treat None as "data unavailable" and avoid raising alerts.

    Note: counts ALL established TCP connections, not just :443. Most modern
    egress is TLS on 443 anyway, and many MCP servers use other ports, so
    a broader count is more useful than the historical :443-only filter.
    """
    ps_script = (
        "$c = Get-NetTCPConnection -State Established -ErrorAction SilentlyContinue;"
        "$total = if ($c) { $c.Count } else { 0 };"
        "$g = $c | Group-Object OwningProcess | Sort-Object Count -Descending | "
        f"Select-Object -First {int(top_n)};"
        "$rows = foreach ($x in $g) {"
        "  $p = Get-Process -Id $x.Name -ErrorAction SilentlyContinue;"
        "  $name = if ($p) { $p.ProcessName } else { 'gone' };"
        "  $cmd = '';"
        "  if ($p) {"
        "    $ci = Get-CimInstance Win32_Process -Filter \"ProcessId = $($x.Name)\" "
        "-ErrorAction SilentlyContinue;"
        "    if ($ci -and $ci.CommandLine) { "
        "$cmd = $ci.CommandLine.Substring(0, [Math]::Min(80, $ci.CommandLine.Length)) "
        "}"
        "  };"
        "  '{0}|{1}|{2}' -f $x.Count, $name, $cmd"
        "};"
        "Write-Output \"TOTAL=$total\";"
        "$rows | ForEach-Object { Write-Output $_ }"
    )

    try:
        result = subprocess.run(
            ["powershell", "-NoProfile", "-Command", ps_script],
            capture_output=True, text=True, encoding="utf-8",
            errors="replace", timeout=timeout,
        )
    except (OSError, subprocess.TimeoutExpired):
        return None, []

    if result.returncode != 0:
        return None, []

    total: int | None = None
    holders: list[Holder] = []
    for ln in result.stdout.splitlines():
        ln = ln.strip()
        if not ln:
            continue
        if ln.startswith("TOTAL="):
            try:
                total = int(ln.split("=", 1)[1])
            except ValueError:
                pass
        elif "|" in ln:
            parts = ln.split("|", 2)
            if len(parts) == 3:
                try:
                    cnt = int(parts[0])
                except ValueError:
                    continue
                # ASCII-strip the cmd hint to satisfy the cp1252 steering rule
                # (this output is printed to Task Scheduler / hook stdout).
                cmd = parts[2].encode("ascii", errors="replace").decode("ascii")
                holders.append(Holder(name=parts[1], count=cnt, cmd_hint=cmd))

    return total, holders


def format_top_holders(holders: list[Holder], max_cmd_chars: int = 40) -> str:
    """Format top holders as a compact one-line string for alert details."""
    if not holders:
        return "no per-process data"
    parts = []
    for h in holders:
        cmd = h.cmd_hint.strip()
        if cmd:
            # Strip the python.exe path prefix if present, keep the script name
            for marker in ("python.exe ", "python.exe\" "):
                if marker in cmd:
                    cmd = cmd.split(marker, 1)[1]
                    break
            cmd = cmd[:max_cmd_chars]
            parts.append(f"{h.name}({cmd})={h.count}")
        else:
            parts.append(f"{h.name}={h.count}")
    return ", ".join(parts)
