# Incident Triage Steering Rules

> Loaded via Context Routing when topics include: OOM, RCA, root cause, post-mortem, drain, memory pressure, incident, thrash, pagefile, preflight.
>
> Owner: Jarvis overnight + live-incident response. Rules here apply to diagnostic work, not to general build/workflow.

## RCA Discipline

### R1. Confidence ceiling under endpoint-only measurement

**Rule**: For any system-level RCA where measurements are endpoint-only (no data points within the failure window), written confidence is capped at LOW-MEDIUM regardless of circumstantial-evidence quality.

**Why**: 2026-04-18 overnight OOM RCA declared HIGH confidence on two 04:45-preflight pagefile snapshots + zombie-process timing alignment. Collapsed to LOW-MEDIUM under a single Eric question: "should we not get an actual memory usage report of each overnight cron task?" Circumstantial plausibility had been masquerading as evidence.

**How to apply**:
- Every RCA doc must have an explicit "Instrumentation gap" subsection alongside the theory section. Write the gap as a deliverable, not an afterthought.
- If the instrumentation-gap subsection is non-empty, the document's stated confidence cannot exceed MEDIUM.
- The follow-up session's P1 scope item must be instrumentation, not remediation. Shipping a fix on endpoint-only evidence is guessing with a ticket number.

### R2. CIM/WMI hang under load is itself a diagnostic — do not wait for a "real" measurement

**Rule**: When `Get-CimInstance` or other normally-sub-second diagnostic cmdlets stall for 30 s or more, treat as confirmed memory thrash and skip to triage actions.

**Why**: During the 2026-04-18 13:00 live OOM, `Get-CimInstance Win32_OperatingSystem` and `Get-CimInstance Win32_PageFileUsage` both hung past 30 s while `Get-Process` still returned promptly. Eric reported Task Manager would not open during the same window. When the delayed CIM call eventually returned (~26 min later), it returned zeroes with a "Shutting down" error — WMI itself was tearing down under pressure.

**How to apply**:
- If CIM hangs, stop diagnosing and act. Issue targeted `Stop-Process -Id <PID> -Force` for known zombies (node.exe from prior sessions, old claude.exe clusters), followed by `shutdown /r /t 0` if pressure persists.
- Do not launch additional diagnostic PS calls — they will queue behind the hung CIM and compound the problem.
- Add timeout-wrapped diagnostics to any future triage playbook (`Invoke-Command -AsJob` with short timeout) to avoid this failure mode.

### R3. Sum-process-commit is the simplest continuous memory logger

**Rule**: For continuous memory-pressure monitoring, `(Get-Process | Measure-Object PagedMemorySize -Sum).Sum` is sufficient — do not reach for CIM or performance counters first.

**Why**: The delayed 2026-04-18 13:00 PowerShell job returned exactly one useful value while CIM was failing: **Sum process commit: 119.69 GB** on a 32 GB physical + 86 GB pagefile system. That single number named the incident. Performance counters (`Get-Counter '\Memory\Committed Bytes'`) and CIM hang under load; `Get-Process` does not.

**How to apply**:
- The 15-min memory logger writing to `data/logs/memory_timeseries.jsonl` (Session B2 P1) should emit `sum_commit_bytes` as its core field, sourced from `Get-Process`, not CIM.
- Tag each tick with top-5 processes by `PagedMemorySize` so the logger also names the consumer, not just the total.
- Alert threshold: sum-commit above pagefile-allocated size. That crossing means over-commit in progress — the system is buying time via swap-to-disk, and the preflight window is already blown.

## Investigation Sequencing

### I1. Architecture review is mandatory when 2+ prior fixes failed (migrated from CLAUDE.md)

Retained here for local ownership of the RCA/incident domain. See CLAUDE.md Workflow Discipline for the original phrasing; this is its permanent home once that entry is pruned.

(Entry deferred — CLAUDE.md rule remains authoritative until next `/update-steering-rules --audit` relocates it.)
