# Overnight OOM Investigation — Checkpoint

**Incident**: 2026-04-18 morning — Windows OOM dialog, Task Manager malformed, bun crash launching `claude` CLI in epdev repo.
**Status**: Diagnosed upstream cause; root culprit not yet identified. Two follow-up sessions queued.

## What we know (evidence)

### This morning's overnight (data/logs/overnight_2026-04-18.log)
```
04:45:01  Overnight self-improvement starting
          Pre-flight memory: LOW PAGEFILE:
            phys=9.5GB free / 31.9GB total
            pagefile=0.7GB free / 86.0GB total
            load=70%
          ERROR: Available pagefile below threshold. Skipping tonight's run.
04:45:33  Overnight complete (exit code: 0)  [preflight aborted in 32s]
```

### Yesterday's baseline (data/logs/overnight_2026-04-17.log)
```
04:45:01  Pre-flight: phys=22.3GB free / 31.9GB | pagefile=80.6GB free / 103.8GB | load=30%
          Full 6-dimension run completed in 91 min
06:18:07  Overnight complete (exit code: 0)  [self-diagnose fired once for QUALITY_GATE fail]
```

### Key delta
Between **06:18 on 04-17** and **04:45 on 04-18** (~22.5 hours), pagefile dropped from 80.6GB free → 0.7GB free. **~80GB pagefile consumed** with no overnight_runner active.
Pagefile total also dropped 103.8GB → 86.0GB (Windows dynamic-expand contracted — consistent with a process releasing but leaving the system pressured).

### Preflight worked
`check_memory_preflight()` in overnight_runner.py fired correctly. Overnight is **not** the culprit for this incident.

## Suspect schedulers (all invoke `claude -p`)

From `tools/scripts/reschedule_overnight.ps1`:

| Time  | Task                            | Preflight? | claude_lock? | Suspicion |
|-------|---------------------------------|------------|--------------|-----------|
| 04:00 | Jarvis-ParadigmHealth           | **UNKNOWN** | **UNKNOWN**  | HIGH — runs 45min before overnight; if it leaked, overnight preflight at 04:45 would see the damage |
| 04:45 | Jarvis-Autoresearch-CodeQuality | YES (aborted today) | YES (confirmed) | cleared — preflight-guarded |
| 07:15 | Jarvis-TELOS-Introspection      | **UNKNOWN** | **UNKNOWN**  | MEDIUM — post-overnight, could stack on leftover load |
| 08:00 | Jarvis-Security-Audit           | **UNKNOWN** | **UNKNOWN**  | MEDIUM — same |
| hourly | run_heartbeat.bat              | NO         | NO           | LOW — small Python jobs but ran 22× between incidents |

Lock coverage confirmed only in 4 scripts: `worktree.py`, `overnight_runner.py`, `jarvis_dispatcher.py`, `jarvis_autoresearch.py`.

## Open questions

**For memory investigation session:**
1. Which `.bat` wrapper does Jarvis-ParadigmHealth invoke? Does it call claude -p? Does it preflight-check? Does it acquire claude_lock?
2. Same three questions for Jarvis-TELOS-Introspection and Jarvis-Security-Audit.
3. Are there zombie claude/bun processes still resident right now? `Get-Process | Where-Object { $_.Name -match 'bun|node|claude' }`
4. What does `data/logs/paradigm_health_2026-04-17.log` (and TELOS, security-audit) show for memory/duration?
5. Does any of these three scripts spawn long-running background sub-processes that could leak?
6. Windows Event Viewer: any `Application Error` / `Windows Error Reporting` entries between 06:18 04-17 and 04:45 04-18?

**For architecture-review session (after investigation concludes):**
- Given the confirmed culprit, is the fix "add preflight to the 3 tasks" or something more structural?
- Is `claude_lock` the right primitive, or should we move to a scheduler-level memory budget?
- Should nested `claude -p` inside overnight_runner (quality-gate, security-audit, synthesize pre-check) be replaced with Python+rg?
- Loop-closure risk: do any of these autonomous tasks generate signals that feed back into their own triggers?

## Proposed fix (ranked, from prior synthesis)

| # | Lever | Memory delta | Effort |
|---|---|---|---|
| 1 | Add preflight guard to the 3 unguarded claude -p schedulers | Prevents recurrence | ~30 min |
| 2 | Verify claude_lock coverage on all 6 claude-invoking schedulers | Prevents 2× concurrent = 600-1000MB overlap | ~20 min |
| 3 | Replace nested claude -p inside overnight_runner with Python+rg | -900MB to -1.5GB overnight peak | ~2 hrs |
| 4 | Ship pending pagefile increase (16/32 → 64GB) | Headroom insurance | 5 min + reboot |
| 5 | Consolidate heartbeat.bat 5 sequential Python scripts | 160MB temporal, cosmetic | ~1 hr |

## Investigation Results (2026-04-18 session)

### Culprit identified: 9 stale `claude.exe` from Eric's interactive session on 04-17

**Evidence chain:**
- `data/logs/session_cleanup_2026-04-18.log` at 00:30:01 killed 9 `claude.exe` PIDs **aged 14.7 hours** — i.e. spawned ~09:48 on 04-17.
- `data/logs/session_cleanup_2026-04-17.log` at 00:38:12 killed 9 processes aged 10.1 hours (prior day baseline).
- Drain window is 06:18 04-17 → 04:45 04-18; the 14.7h zombie lifespan covers 09:48 04-17 → 00:30 04-18 — **spans the entire drain window**.
- Baseline-to-incident delta: +4.6 hours of accumulated leak time vs typical day (~45% longer).
- Scale math: 9 processes × ~7–9 GB commit-growth each ≈ 60–80 GB — matches observed 62 GB commit growth.
- These processes are Eric's interactive Claude Code CLI (one CLI session spawns ~9 `claude.exe` helpers). Explorer/TextInputHost StartTimes at 09:49:06 confirm user logon began at that time.
- **No scheduled Jarvis task spawns at 09:48 AM** — `MorningFeed` at 09:00 is pure Python+RSS, completed in normal pattern with no claude subprocess.

### Three suspected schedulers — rulings

| Task | Wrapper | `claude -p`? | Preflight? | `claude_lock`? | 04-17 runtime | Ruling |
|---|---|---|---|---|---|---|
| Jarvis-ParadigmHealth (04:00) | `run_paradigm_health.bat` | **NO** (pure Python, `paradigm_health.py`) | N/A | N/A | 1.7 s | **EXONERATED** |
| Jarvis-TELOS-Introspection (07:15) | `run_autoresearch.bat` → `self_diagnose_wrapper.py` → `jarvis_autoresearch.py` | YES (nested inside autoresearch) | via `self_diagnose_wrapper` | YES (confirmed in checkpoint line 45) | 4m 38s | **EXONERATED** for this incident |
| Jarvis-Security-Audit (08:00) | `run_security_audit.bat` | **YES (direct, unguarded)** | **NO** | **NO** | 2m 23s | **EXONERATED** for this incident (ran clean), but **ARCHITECTURAL RISK remains** — 72h `Stop Task` timeout means a hang could leak for 3 days |

### Windows Event Viewer — drain window (06:18 04-17 → 04:45 04-18)
- `Get-WinEvent` Level 2 (Error) filter: **no `Application Error`, no `Windows Error Reporting`, no OOM-killer signatures**.
- Only entries: benign `Microsoft-Windows-Security-SPP` license-activation failures.
- **Implication**: leak was gradual commit accumulation, not a crash-restart cycle.

### Current system state (snapshot at 12:18 PM 04-18)
- 11 `claude.exe` processes totalling **~2.5 GB commit** (9 started 12:47:48 AM 04-18, 2 from current Eric session at 12:17–12:18 PM). Not lingering-leak scale.
- **3 zombie `node.exe` from 04-17 09:51 AM still alive** (PID 15564, 24712, 24804) — combined ~800 MB commit. `SessionCleanup` only targets `claude.exe`; node helpers survive and persist across cleanups. Not the primary driver but a permanent minor leak.
- Top-15 commit system-wide: ~3.5 GB total. No lingering 80 GB allocator visible — confirming the drain was in the killed processes.

### Why pagefile was still 0.7 GB free at 04:45 despite SessionCleanup at 00:30
- Windows dynamic pagefile contracted 103.8 GB → 86 GB in the window — consistent with allocator release but OS had not reclaimed/resized cleanly.
- 10 new `claude.exe` spawned at 12:47:48 AM on 04-18 (2h 17m after cleanup) from an unidentified trigger — current commit small, but peak between 12:47 and 04:45 is unknown. Possible secondary contributor.
- Candidate triggers during 00:30–04:45 window: `Jarvis-IndexUpdate` (01:00), `Jarvis-ISCProducer` (02:00). Logs not yet inspected for claude-spawn behaviour — flag for Session B if the primary-culprit thesis needs reinforcement.

### Confidence — REVISED (Eric pushback, 2026-04-18 12:30)

**Original thesis (daytime zombies, HIGH confidence) is downgraded to LOW-MEDIUM.** Eric correctly flagged that (a) the two pagefile data points are both 04:45-preflight readings — there is **no measurement between them** — so "gradual daytime drain" was inferred, not observed; (b) OOM symptoms are only ever surfaced overnight because nothing measures pagefile during the day.

### New evidence supporting overnight-drain hypothesis
- **Heartbeat duration trend on 04-18** (hourly, pure-Python job, ~66 MB footprint):
  | Time | Duration |
  |------|----------|
  | 00:00 | 6.5 s |
  | 01:00 | 3.6 s |
  | 02:00 | 4.2 s |
  | 03:00 | 9.8 s ↑ |
  | 04:00 | 17.1 s ↑ |
  | 05:00 | 23.8 s ↑ |
  | 06:00 | 29.6 s ↑ |
- A small Python job slowing **4.5× between 00:00 and 06:00** is a classic pagefile-thrash signature — system IS under growing memory pressure overnight. This is DURING the window, not inferred from endpoints.
- Inflection appears between 02:00 and 03:00 on 04-18 — something started consuming commit around then.

### Paradox: scheduled overnight tasks are tiny
Inspected every scheduled task 00:30 → 04:45 on 04-18:
| Time | Task | Duration | `claude -p`? | Verdict |
|---|---|---|---|---|
| 00:30 | SessionCleanup | 2 s | no | clean |
| 01:00 | IndexUpdate | 0.11 s | no | clean |
| 02:00 | ISCProducer | 62.7 s (25 Python subprocs) | no | clean |
| 03:00 | ResearchProducer | 0.25 s — **crashed `PermissionError` on log file** | no | crashed |
| 04:00 | ParadigmHealth | 1.7 s | no | clean |
| hourly | Heartbeat | see trend above | no | slowing |

Total overnight CPU work ≈ **68 s**. None call `claude -p`. None can plausibly commit 62 GB. Yet the pressure clearly grew during exactly this window.

### Implication
The drain is **not** from scheduled tasks directly. It is from something running *through* the overnight window that is not a scheduled-task short job. Candidates:
1. A long-running interactive process Eric left open (Claude Code session, Electron app, Docker, dev server) with a slow leak that accelerates.
2. A process spawned by `SessionCleanup` aftermath or by the `ResearchProducer` crash — the 03:00 PermissionError on the log file means *something else was holding that file handle*. Needs root-cause investigation.
3. `claude_lock` + stale subprocess: previous session's claude process holding resources.
4. Kernel/driver pool-paged growth (less likely but possible).

### Ruling on original three suspect schedulers — unchanged
ParadigmHealth, TELOS-Introspection, and Security-Audit all ran clean on 04-17 and 04-18. None of them ran in the 00:30 → 04:45 overnight window. **All three remain exonerated for this incident.** The architectural risk of unguarded `claude -p` in `run_security_audit.bat` still stands for future prevention.

### Critical gap — Eric's proposal is the right fix
**We have no per-task memory instrumentation.** The entire investigation is reasoning from two preflight snapshots plus duration proxies. Session B must include:
1. **Per-task memory probe**: wrap each overnight `.bat` with a pre/post memory snapshot logged alongside its normal log (physical free, pagefile free, committed bytes).
2. **Hourly pagefile logger**: independent Windows scheduled task every 15 min that appends pagefile/phys/commit to `data/logs/memory_timeseries.jsonl` — gives continuous visibility instead of once-daily.
3. **Identify the 02:00 → 03:00 inflection**: once (2) is in place, next OOM will pinpoint the actual consumer.
4. **Investigate `ResearchProducer` log PermissionError at 03:00 04-18**: the fact that a .bat script lost its own log file handle mid-run is evidence of filesystem/process contention that could correlate with the memory pressure window.

### 2026-04-18 13:00 live-incident measurement (hard evidence)

During a second OOM event Eric reported at 13:00 (same day as the overnight preflight abort), a `Get-CimInstance`-based diagnostic hung for ~26 minutes before eventually returning. The one usable number from that stalled job:

- **Sum process commit: 119.69 GB** on a 32 GB physical + ~86 GB pagefile system
- CIM returned `PHYS: 0 GB free of 0 GB` / `PAGEFILE used: blank` with error "Get-CimInstance : Shutting down" (WMI tearing down under pressure)
- Task Manager would not open during the same window

**Significance**: 119.69 GB total commit on a ~118 GB total committable budget (RAM + pagefile) is the first hard mid-window measurement we have. It confirms:
1. The overnight drain thesis is correct in shape — commit overruns total committable memory.
2. A continuous 15-min logger of `(Get-Process | Measure-Object PagedMemorySize -Sum).Sum` would have named this incident in real time.
3. CIM-based telemetry is useless under the exact conditions we need it — the replacement logger must use `Get-Process` (see `orchestration/steering/incident-triage.md` rule R3).

### Session B scope
- [P1] Add memory instrumentation (per-task + hourly timeseries) **before** attempting any fix
- [P2] Investigate ResearchProducer PermissionError root cause
- [P3] Address unguarded `claude -p` in `run_security_audit.bat`
- [P4] Investigate 12:47 AM 04-18 claude spawn cluster origin (unknown trigger)
- [P5] Evaluate `node.exe` zombies from 04-17 09:51 still alive (SessionCleanup only targets `claude.exe`)
- [P6] Pending pagefile increase 32GB → 64GB as headroom insurance

## Reference files (for next session to read)
- `tools/scripts/overnight_runner.py` — lines around `check_memory_preflight()`
- `tools/scripts/self_diagnose_wrapper.py` — OOM detection + short-circuit
- `tools/scripts/reschedule_overnight.ps1` — full schedule
- `tools/scripts/run_overnight_jarvis.bat`, `run_heartbeat.bat`, `run_dispatcher.bat` — wrapper pattern
- `data/logs/overnight_2026-04-17.log`, `overnight_2026-04-18.log`
- `data/overnight_state.json`
- Prior OOM diagnosis: **2026-04-10** (pagefile increase noted as pending since then)
