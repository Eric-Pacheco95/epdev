# Overnight OOM + Live Thrash — Session Triage Handoff

**Date**: 2026-04-18
**Author session**: covered overnight preflight abort (04:45 AM) + live incident (13:00 PM) + learning capture + steering-rule update
**Canonical evidence source**: `memory/work/_overnight-oom-2026-04-18/CHECKPOINT.md`
**Prior handoff (Session B1)**: `memory/work/_overnight-oom-2026-04-18/SESSION_B_HANDOFF.md`

---

## Two incidents, one day

### Incident A — overnight preflight abort (04:45 AM 04-18)
- Pagefile 0.7 GB free of 86 GB (vs 80.6 GB free of 103.8 GB at same time prior day) — **~62 GB commit growth over 24 h**
- `check_memory_preflight()` fired correctly; overnight runner aborted cleanly. Preflight worked.

### Incident B — live thrash (~13:00 PM 04-18)
- Eric: "I can't even open Task Manager"
- Two back-to-back `Get-CimInstance` PS calls hung 30 s+ (classic thrash signature)
- One delayed call eventually returned **Sum process commit: 119.69 GB** on a 32 GB RAM + ~86 GB pagefile box = over-committed past the total committable budget
- CIM returned "Shutting down" error when it finally unstuck (WMI service tearing down under pressure)

---

## What we know (hard evidence)

1. **Two pagefile endpoints** (both 04:45 preflights): 80.6 GB free → 0.7 GB free
2. **Heartbeat duration trend 04-18 (pure-Python hourly job as ambient pressure proxy)**:
   | Time | Dur |
   |---|---|
   | 00:00 | 6.5 s |
   | 01:00 | 3.6 s |
   | 02:00 | 4.2 s |
   | 03:00 | 9.8 s ↑ |
   | 04:00 | 17.1 s ↑ |
   | 05:00 | 23.8 s ↑ |
   | 06:00 | 29.6 s ↑ |
   Inflection between 02:00 and 03:00 — pressure grew DURING overnight window.
3. **All scheduled tasks 00:30 → 04:45 totalled ~68 s CPU, zero `claude -p` calls** (SessionCleanup 2s, IndexUpdate 0.11s, ISCProducer 62.7s, ResearchProducer crashed at 0.25s on PermissionError, ParadigmHealth 1.7s). Scheduled tasks cannot themselves explain the drain.
4. **Live thrash: 119.69 GB sum process commit** (hard mid-window measurement)
5. **ResearchProducer crashed 03:00 04-18 with `PermissionError` on its own log file** — process contention evidence at the inflection point
6. **No Windows Event Viewer errors in overnight window** (only benign SPP license activations) — gradual accumulation, not crash-restart cycle
7. **Zombies at time of investigation**:
   - 3 × node.exe from 04-17 09:51 AM still alive (SessionCleanup only kills claude.exe)
   - 10 × claude.exe spawned 00:47:48 AM 04-18 from unknown trigger (no matching scheduled task)

## Theories (ranked)

| # | Theory | Confidence |
|---|---|---|
| 1 | Long-running non-scheduled process leaking through the night (interactive session, Electron app, Docker, dev server) | MEDIUM — supported by heartbeat trend + 119.69 GB live measurement + no matching scheduled task |
| 2 | Daytime interactive Claude Code session zombies (9 × claude.exe, 14.7 h old killed by SessionCleanup at 00:30) | LOW-MEDIUM — timing plausible but no mid-window daytime evidence |
| 3 | ResearchProducer 03:00 PermissionError correlates with inflection | LOW — worth chasing |
| 4 | Originally-suspected schedulers (ParadigmHealth, TELOS-Introspection, Security-Audit) | RULED OUT — clean runs, wrong time-of-day |

**Note**: Session A declared "HIGH" confidence on theory 2 from endpoint-only evidence. Downgraded after Eric pushback. This failure mode spawned steering rule R1 below.

## What we don't know and must measure

- WHEN during the 24 h window commit actually grew (heartbeat trend tells us "overnight" but not which hour bucket)
- WHICH process(es) drove the 119.69 GB commit at 13:00 (we have the total, not the top consumers)
- WHAT triggered the 10-claude.exe cluster at 00:47:48 AM 04-18
- WHY ResearchProducer lost its log-file handle at 03:00 04-18

---

## New steering rule (persisted this session)

Written to `orchestration/steering/incident-triage.md` (new sub-steering file). Context Routing entry added to `CLAUDE.md` keyed on topics: OOM, RCA, root cause, post-mortem, drain, memory pressure, incident, thrash, pagefile, preflight.

Three rules captured:
- **R1 Confidence ceiling under endpoint-only measurement** — if no data points WITHIN the failure window, written confidence capped at LOW-MEDIUM; every RCA doc must have an "Instrumentation gap" subsection; follow-up P1 must be instrumentation, not remediation.
- **R2 CIM/WMI hang is itself a diagnostic** — if `Get-CimInstance` stalls 30 s+, stop diagnosing, skip to `Stop-Process -Force` by PID or `shutdown /r /t 0`. Do not queue more PS diagnostics.
- **R3 Sum-process-commit is the simplest continuous logger** — use `(Get-Process | Measure-Object PagedMemorySize -Sum).Sum`, not CIM or performance counters. CIM hangs under load; `Get-Process` does not.

## Signals written (5) + failure (1)

Stored in `memory/learning/signals/` and `memory/learning/failures/`:
- `2026-04-18_endpoint-only-measurements-bound-rca-confidence.md` (A/8)
- `2026-04-18_instrument-before-fix-for-rca.md` (A/9)
- `2026-04-18_heartbeat-duration-as-ambient-memory-pressure-proxy.md` (B/7)
- `2026-04-18_cim-wmi-hang-is-itself-a-memory-pressure-signal.md` (B/6)
- `2026-04-18_anomaly-10-claude-cluster-00-47-04-18.md` (B/6)
- `2026-04-18_high-confidence-rca-on-circumstantial-evidence.md` (failure, sev 7)

---

## Session B2 scope (priority order — instrumentation first)

1. **[P1]** Per-task memory probe — wrap every overnight `.bat` with pre/post snapshot of `(Get-Process | Measure-Object PagedMemorySize -Sum).Sum`, physical free, pagefile free. Log alongside normal task log.
2. **[P1]** Independent 15-min pagefile logger — new scheduled task writing JSONL to `data/logs/memory_timeseries.jsonl`. Core field: `sum_commit_bytes` from `Get-Process` (NOT CIM, per rule R3). Tag each tick with top-5 processes by `PagedMemorySize`. Alert when sum-commit crosses pagefile-allocated size.
3. **[P2]** Investigate ResearchProducer 03:00 PermissionError — identify the other process holding its log-file handle.
4. **[P2]** Identify the 00:47:48 AM 04-18 10-claude.exe cluster trigger — search `tools/scripts/**/*.py` for `subprocess.*claude`; cross-reference `history/sessions/` and `data/overnight_state.json`.
5. **[P3]** Add preflight + `claude_lock` to `run_security_audit.bat` (architectural risk, not cause of this incident — 72 h `Stop Task` timeout on unguarded `claude -p`).
6. **[P3]** Extend SessionCleanup to cover `node.exe` zombies too — currently only targets `claude.exe`; 3 × node from 04-17 09:51 survived across cleanup.
7. **[P4]** Ship pending pagefile increase 32 GB → 64 GB (pending since 2026-04-10 prior OOM).
8. **[P4]** Consider lowering SessionCleanup threshold from 8 h → 4 h if daytime-leak thesis is confirmed post-instrumentation.

## Non-goals for Session B2

- Do NOT propose remediations before the P1/P1 instrumentation is live and has captured at least one observable mid-window event. Rule R1 makes this explicit.
- Do NOT re-investigate ParadigmHealth / TELOS-Introspection / Security-Audit as OOM causes. Ruled out on this incident.
- Do NOT write HIGH-confidence RCA sections in any follow-up document until instrumentation data is available.

## Files to read first (Session B2 cold start)

1. `CLAUDE.md` — Context Routing table now includes `incident-triage.md` entry
2. `orchestration/steering/incident-triage.md` — three new RCA steering rules (R1/R2/R3)
3. `memory/work/_overnight-oom-2026-04-18/CHECKPOINT.md` — full evidence chain including 13:00 live-incident subsection
4. `memory/work/_overnight-oom-2026-04-18/SESSION_B_HANDOFF.md` — B1 handoff (supersedes some; this triage file is newer)
5. `data/logs/heartbeat_2026-04-18.log` — duration-trend evidence
6. `tools/scripts/overnight_runner.py` — `check_memory_preflight()` to model the new logger after
7. `tools/scripts/session_cleanup.py` — 8 h threshold, claude.exe-only scope
8. `tools/scripts/reschedule_overnight.ps1` — authoritative schedule definition
