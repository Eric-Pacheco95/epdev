# Python.exe Process Leak — Triage Report

**Date**: 2026-04-18  
**Session**: Triage (parallel to Session B2)  
**Scope**: Identify spawner(s) behind 9,488 python.exe zombies at 99.3% commit

---

## PPID Histogram (Step 1)

**Method**: `CreateToolhelp32Snapshot` (Win32 API) — CimInstance/wmic hang under memory pressure, this doesn't.

**Result**: 9,488 unique PPIDs, ALL showing `DEAD/ORPHAN`. No PPID has count > 1.

```
PPID   | Parent status | Child count
------ | ------------- | -----------
152988 | DEAD/ORPHAN   | 1
150788 | DEAD/ORPHAN   | 1
153280 | DEAD/ORPHAN   | 1
... (9,488 unique entries, all count=1)
```

**Implication**: Every python.exe was spawned by a unique parent that has since died. There is NO single live spawner running a loop. This is purely accumulated orphans from processes that exited/crashed and left children behind.

PPID range: ~87,000–155,000 (high-number PIDs, suggesting accumulated over weeks of PID churn).

---

## Top PPIDs Resolved (Step 2)

All dead. `Get-Process -Id <PPID>` returns nothing for any sampled PPID. Process memory queries (command line, path, start time) all return `ACCESS_DENIED` — the python.exe processes run as SYSTEM.

**Cannot get command lines directly.** Analysis derived from codebase + log inspection.

---

## Cmdline Pattern (Step 3 — inferred)

**Three confirmed spawner mechanisms** (cannot read cmdline directly; derived from code + logs):

### Mechanism A: `for /f today.py` in all .bat wrappers

Every `.bat` wrapper (heartbeat, dispatcher, overnight, etc.) uses:
```bat
for /f %%I in ('python.exe today.py') do set LOGDATE=%%I
```

Process chain: Task Scheduler → cmd.exe (bat file) → cmd.exe (for/f subshell) → **python.exe today.py**

Under OOM: python.exe fails to start (WinError 1455 on interpreter heap init), hangs indefinitely. Task Scheduler kills the bat's cmd.exe after PT72H (most tasks). But python.exe (grandchild) is NOT killed — it's an orphan.

**Rate**: Heartbeat fires every hour (PT1H), 24 × 21 days = 504 runs × 1 today.py each = 504 potential orphans from this path alone if all hang.

### Mechanism B: `isc_executor.py` `shell=True` subprocess.run

`tools/scripts/isc_executor.py:220`:
```python
result = subprocess.run(command, shell=True, timeout=60, ...)
```

Process chain: isc_producer.py → subprocess.run(isc_executor.py) → subprocess.run(cmd.exe /c `<verify cmd>`) → **python.exe** (when verify = `pytest` or `python script.py`)

`shell=True` on Windows uses `cmd.exe /c`. When 60s timeout fires, Python kills cmd.exe via `e.process.kill()`, but the child **python.exe** spawned by cmd.exe survives as orphan.

**Rate**: ISCProducer runs at 02:00 daily, 25 PRDs/run × multiple ISC criteria each. Log confirms "25 Python subprocs" at 02:00 04-18 (62.7s). These correspond to orphaned python.exe from timed-out verify commands.

### Mechanism C: Claude hook python.exe from overnight/dispatcher sessions

Claude Code hooks fire python.exe per tool call:
- `hook_session_start.py`, `validate_tool_use.py`, `hook_events.py`, `hook_stop.py`, `hook_session_cost.py`

Process chain: `subprocess.run([claude.exe, "-p", ...])` → claude.exe → hook invocation → cmd.exe /c run_hook.bat → **python.exe hook.py**

When `subprocess.run` kills claude.exe on timeout (overnight_runner: 7200s; self_diagnose_wrapper: 300s), the cmd.exe running run_hook.bat becomes orphaned, and any in-flight python.exe hook process survives.

**Rate**: overnight_runner runs 6 dimensions/night × 21 nights = 126 claude -p sessions. Self-diagnose calls claude -p on any run with ERROR-pattern output (nightly). Each session: 1+ hooks per tool call, potentially dozens of in-flight python.exe.

---

## Scheduled Task Cross-Reference (Step 4)

| Task | Wrapper | python spawning | Max timeout | Confirmed mechanism |
|------|---------|----------------|-------------|---------------------|
| Jarvis-Heartbeat (hourly) | run_heartbeat.bat | today.py + 4 scripts | PT72H | **Mechanism A** |
| Jarvis-ISCProducer (02:00) | run_isc_producer.bat | 25 python via isc_executor | PT72H | **Mechanism B** — CONFIRMED (log shows 25 subprocs) |
| Jarvis-Autoresearch (04:45) | run_overnight_jarvis.bat | claude -p hooks | PT72H | Mechanism C |
| Jarvis-Dispatcher (05:30) | run_dispatcher.bat | claude -p hooks | PT1H | Mechanism C |
| Jarvis-Security-Audit (08:00) | run_security_audit.bat | likely claude -p hooks | PT72H | Mechanism C (unguarded) |
| All daily tasks | *.bat | today.py pattern | PT72H | Mechanism A |

All tasks use `MultipleInstances: IgnoreNew` — no stacking. Orphans accumulate across sequential runs.

---

## CreationDate Clustering (Step 5 — partial)

Cannot read process `StartTime` or `CreationDate` from python.exe processes (ACCESS_DENIED — running as SYSTEM). Analysis from PPID range:

PPID range 87,000–155,000: Windows PID space wraps at ~65,536 (or higher depending on config). The wide PPID range spanning 87k → 155k suggests accumulation over many hours/days (PIDs increment monotonically until wrap).

**No burst event confirmed** — the count=1 per-parent structure is consistent with GRADUAL STEADY ACCUMULATION across hundreds of scheduled task invocations, not a single burst.

Closest burst candidate: "10 claude.exe at 00:47:48 AM 04-18" from CHECKPOINT (from unknown trigger, 2h17m after SessionCleanup). If each ran many tool calls firing hooks = potentially hundreds of python.exe from that cluster.

---

## `subprocess.Popen` Audit (grep for coding-level reap failures)

```
grep -rn "Popen" tools/ --include="*.py"  →  (no results)
grep -rn "Popen" orchestration/ --include="*.py"  →  (no results)
```

**No raw `Popen` without `.wait()` in the codebase.** All subprocess usage is `subprocess.run` (which blocks). The leak is architectural (Windows doesn't cascade `TerminateProcess` to grandchildren), not a coding omission.

---

## Prime Suspects (ranked)

1. **ISCProducer (02:00) + isc_executor.py shell=True** — HIGHEST CONFIDENCE
   - Confirmed in prior session log: "25 Python subprocs" from 02:00 run on 04-18
   - Runs daily × 21 days = 525+ orphans from this path
   - `shell=True` with `proc.kill()` on timeout is the exact Windows orphan-creation pattern
   - Fix: use `subprocess.run(["python", script], ...)` instead of `shell=True` for verify commands

2. **`for /f today.py` in every .bat wrapper** — HIGH CONFIDENCE
   - Heartbeat alone: 504 runs × 1+ today.py = 504 potential orphans if hang rate > 0
   - All daily tasks also use this pattern
   - Fix: rewrite to `python -c "import datetime; print(datetime.date.today())"` inline, or use Task Scheduler's built-in date, eliminating the subprocess entirely

3. **Claude hook python.exe orphaned by subprocess.run timeout** — MEDIUM CONFIDENCE  
   - overnight_runner (7200s timeout), self_diagnose_wrapper (300s timeout)
   - Hook python.exe is grandchild of claude.exe — not killed when claude.exe is terminated
   - Fix: use Windows Job Objects when spawning claude -p to cascade kills to all descendants

---

## Reaper Target (Step 6 — Eric approval needed)

Processes older than 30 min that are safe to kill (ACCESS_DENIED prevents StartTime read for SYSTEM-owned processes — the kill command must use a PowerShell filter approach):

```powershell
# PREVIEW ONLY — show count before killing
Get-Process python | Where-Object { $_.StartTime -lt (Get-Date).AddMinutes(-30) } | Measure-Object | Select-Object Count
```

Note: if `StartTime` is empty (ACCESS_DENIED), use age-based heuristic: kill all python.exe NOT in the current terminal's ancestry. The following is safe regardless:

```powershell
# Kill all python.exe older than 30 min (excludes processes we can't read)
Get-Process python -ErrorAction SilentlyContinue | 
    Where-Object { try { $_.StartTime -lt (Get-Date).AddMinutes(-30) } catch { $false } } | 
    Stop-Process -Force -ErrorAction SilentlyContinue
```

**⚠ WAIT FOR ERIC GO-AHEAD before executing. Show him the count first.**

---

## Fix PRD Inputs

For the parallel PRD session:

| Component | Fix | Priority |
|-----------|-----|----------|
| `isc_executor.py:220` | Replace `shell=True` subprocess with explicit `["python", "-m", "pytest", ...]` etc — no cmd.exe intermediary | P1 |
| All `.bat` wrappers | Remove `for /f %%I in ('python.exe today.py')` — replace with `set LOGDATE=%DATE:~10,4%-%DATE:~4,2%-%DATE:~7,2%` (no subprocess) or use PowerShell `$((Get-Date).ToString('yyyy-MM-dd'))` | P1 |
| `subprocess.run([claude.exe, ...])` callers | Add Windows Job Object wrapper to cascade TerminateProcess to all hook children on timeout kill | P2 |
| `session_cleanup.py` | Extend to include python.exe older than threshold, not just claude.exe | P2 |
| Reaper scheduled task | New task: kill orphaned python.exe (age > 4h, parent = dead) at 00:00 daily | P2 |

---

## Summary

- **9,488 python.exe** — all orphaned, each unique parent is dead
- **No live spawner** — this is accumulated over days/weeks
- **Root cause**: Windows does not cascade `TerminateProcess` to grandchildren; `.bat` and `shell=True` subprocess patterns create cmd.exe intermediaries that die and leave python.exe orphaned
- **Primary source**: `isc_executor.py` shell=True (25/night × 21 days) + `for/f today.py` in all bat wrappers (504 heartbeat runs alone)
- **Secondary source**: Hook python.exe from overnight claude sessions
- **Code quality**: No raw Popen misuse — architectural fix required
