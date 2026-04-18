# Overnight OOM — Session B Handoff

**Date**: 2026-04-18
**Prior sessions**: Session A (diagnosis) + Session B1 (investigation + Eric pushback). This file loads Session B2.
**Canonical source**: `CHECKPOINT.md` (same directory) — read it first for full evidence chain.

## Incident one-liner

On 2026-04-18 at 04:45, overnight preflight aborted because pagefile was 0.7 GB free of 86 GB (vs 80.6 GB free of 103.8 GB at 04:45 the prior day). Net commit growth **~62 GB** over 24 hours. Preflight worked as designed. Root cause of drain **not confirmed** — only circumstantial evidence.

## What we know (hard evidence)

1. **Two pagefile data points only** — both are 04:45 preflight snapshots. No mid-window measurements.
2. **Heartbeat duration trend on 04-18** proves memory pressure GREW during overnight window:
   - 00:00 → 6.5s | 01:00 → 3.6s | 02:00 → 4.2s | 03:00 → 9.8s | 04:00 → 17.1s | 05:00 → 23.8s | 06:00 → 29.6s
   - Inflection between 02:00 and 03:00 — something started consuming commit around then.
3. **All scheduled tasks 00:30 → 04:45 are tiny** — total ~68s CPU, zero `claude -p` calls:
   - 00:30 SessionCleanup (2s, killed 9 stale claude from 09:48 04-17)
   - 01:00 IndexUpdate (0.11s)
   - 02:00 ISCProducer (62.7s, 25 Python subprocs)
   - 03:00 ResearchProducer (0.25s — crashed `PermissionError` on its own log file)
   - 04:00 ParadigmHealth (1.7s)
   - Hourly Heartbeat (small, but slowing)
4. **Three originally-suspected schedulers all exonerated for this incident**: ParadigmHealth (pure Python), TELOS-Introspection (self_diagnose_wrapper + claude_lock, 4m38s, ran at 07:15 post-preflight), Security-Audit (clean 2m23s, ran at 08:00 post-preflight). Architectural risk remains for Security-Audit (unguarded `claude -p`, 72h max runtime) but it did NOT cause this incident.
5. **No Windows Event Viewer errors** in drain window (only benign SPP license activations). Drain was gradual commit accumulation, not crash-restart cycle.
6. **Zombie processes still alive at time of investigation** (12:18 PM 04-18):
   - 3 × node.exe from 04-17 09:51 AM (SessionCleanup doesn't target node, only claude)
   - 10 × claude.exe from 04-18 00:47:48 AM (unknown trigger — 2h17m after SessionCleanup, currently ~2.5 GB total commit)

## Theories (ranked)

| # | Theory | Confidence | Why |
|---|---|---|---|
| 1 | **Long-running non-scheduled process leaking through the night** (interactive session, Electron app, Docker, dev server) | MEDIUM | Heartbeat slowdown proves pressure grew overnight; scheduled tasks too small to cause it; implies external leak |
| 2 | **Daytime interactive Claude Code session zombies (9 × claude.exe, 14.7h old)** | LOW-MEDIUM | Timing covers window; scale plausible (9 × ~7 GB ≈ 62 GB); but NO evidence daytime commit actually grew — could have been flat and all drain happened overnight |
| 3 | **ResearchProducer PermissionError at 03:00 04-18 correlates with inflection point** — something else holds log-file handle | LOW but worth chasing | Process contention evidence near inflection; needs root-cause investigation |
| 4 | **Originally-suspected schedulers** (ParadigmHealth, TELOS, Security-Audit) | RULED OUT | Evidence in `CHECKPOINT.md` — all clean/unrelated to incident timing |

## Critical gap

**We have no per-task memory instrumentation.** The entire RCA is reasoning from two endpoints plus duration proxies. Eric correctly insisted that instrumentation must come before any fix attempt — otherwise the next OOM will be diagnosed by the same handwaving.

## Session B2 scope (priority order)

1. **[P1 — MUST BE FIRST]** Add per-task memory probe in every overnight `.bat` wrapper — pre/post snapshot of physical free, pagefile free, committed bytes — logged alongside normal log.
2. **[P1]** Create independent 15-min pagefile logger as a standalone scheduled task writing JSONL to `data/logs/memory_timeseries.jsonl` — continuous visibility replaces once-daily preflight.
3. **[P2]** Investigate ResearchProducer 03:00 04-18 PermissionError — what process held the log file handle. Grep for overlapping process lifetimes.
4. **[P2]** Identify what spawned the 10 × claude.exe cluster at 00:47:48 AM on 04-18 (2h17m after SessionCleanup, no obvious scheduled trigger).
5. **[P3]** Address unguarded `claude -p` in `run_security_audit.bat` (add preflight + claude_lock). Architectural risk, not cause of this incident.
6. **[P3]** Investigate node.exe zombies — SessionCleanup only targets claude.exe; node survives and persists across cleanups. Consider extending cleanup scope.
7. **[P4]** Ship pending pagefile increase 32GB → 64GB as headroom (noted pending since 2026-04-10 prior OOM).
8. **[P4]** Consider: lower SessionCleanup threshold from 8h to 4h if interactive-session leak is confirmed.

## Files to read (for Session B2)

- `memory/work/_overnight-oom-2026-04-18/CHECKPOINT.md` — full evidence + revised confidence
- `tools/scripts/overnight_runner.py` — `check_memory_preflight()`
- `tools/scripts/self_diagnose_wrapper.py` — OOM detection wrapper
- `tools/scripts/session_cleanup.py` — 8h threshold for claude.exe kills
- `tools/scripts/reschedule_overnight.ps1` — all scheduled task definitions
- `tools/scripts/research_producer.py` — lines ~720-741 for log-open crash
- `data/logs/overnight_2026-04-17.log`, `overnight_2026-04-18.log`
- `data/logs/heartbeat_2026-04-18.log` — full timeline showing duration growth
- `data/overnight_state.json`

## Non-goals for Session B2

- Do NOT propose memory fixes before instrumentation is live. Eric explicitly flagged this: "Should we not get an actual memory usage report of each overnight cron task?" — answer is yes, and that must come first.
- Do NOT re-investigate the three originally-suspected schedulers (ParadigmHealth/TELOS/Security-Audit). They are ruled out for THIS incident. Security-Audit still has architectural risk that should be fixed, but it is not the OOM culprit.
