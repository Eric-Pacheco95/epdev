---
slug: memory-observability
created: 2026-04-18
status: Phases 1+2+3+5 + FR-010 COMPLETE (Phase 4 FR-006-009 pending; Phase 2 ≥95%-after-48h ISC window 2026-04-20T22:00)
priority: P1
phase: PHASE1-COMPLETE
parent-incident: 2026-04-18 overnight OOM preflight abort + 13:00 live thrash (119.69 GB commit)
related-prds: memory/work/orphan-prevention-oom/PRD.md (PRD-1, ships first)
context-sources:
  - history/decisions/2026-04-18-arch-review-oom-fix-v2.md
  - memory/learning/signals/2026-04-18_arch-review-oom-fix-v2.md
  - memory/work/_overnight-oom-2026-04-18/SESSION_TRIAGE_HANDOFF.md
  - orchestration/steering/incident-triage.md
---

# PRD: Memory Observability Primitive + /vitals Integration

## OVERVIEW

Close the observability blind spot that made the 2026-04-18 overnight OOM invisible until crash by shipping a continuous sum-commit sampler and surfacing its data through `/vitals`. The sampler writes to `data/logs/memory_timeseries.jsonl` at a time-of-day-scaled cadence (2-min 22:00–08:00, 10-min 08:00–22:00) using `(Get-Process | Measure-Object PagedMemorySize -Sum).Sum` per incident-triage rule R3 — never CIM or WMI, which hang under the exact pressure this telemetry is meant to catch. `/vitals` gains a memory panel plus four drill-down flags (`--memory`, `--reaper-log`, `--token-costs`, `--context-files`) so the morning brief can answer "what was the pressure trajectory overnight, and which processes drove it?" — the question Session B1 could not answer from endpoint-only measurements.

## PROBLEM AND GOALS

- Make mid-window memory pressure visible before crash, not after — the 04-17 evening slope of ~3.5 GB/hr would have been catchable 10–14 h before OOM with continuous sampling
- Name the consumer, not just the total — per-tick top-5 processes by `PagedMemorySize` attributes pressure to specific process classes
- Keep the sampler itself non-hazardous under pressure — no CIM, no WMI, no `Get-Counter` (all hang under load; rule R2)
- Surface everything via `/vitals` morning brief — no overnight Slack alerts (Eric QA rejected alert fatigue)
- Ship the primitive (sampler + JSONL) independently of downstream panels so data accrues while visualization iterates

## NON-GOALS

- Overnight Slack alerting (explicitly rejected by Eric; all visibility via morning `/vitals`)
- Kill-on-threshold behavior in the sampler hot path (observation-only; remediation belongs to out-of-band reaper, separate PRD)
- Windows Service conversion in v1 (deferred pending evidence of tick-loss during pressure events — see R1 in RISKS)
- Live token-count rollup (blocked on Claude Code exposing Stop-hook token data; stubbed with placeholder)
- Reaper log panel (blocked on reaper existing; stubbed with placeholder)
- Backfilling historical memory data from heartbeat-duration proxy (archival only; future analysis project)

## USERS AND PERSONAS

- Eric — sole operator, consumes data via `/vitals` morning brief and drill-down flags
- Future incident responder (Eric + Jarvis) — uses `memory_timeseries.jsonl` as the primary evidence source during RCA, per rule R1 (endpoint-only measurements cap confidence at LOW-MEDIUM)

## USER JOURNEYS OR SCENARIOS

1. Morning brief — Eric runs `/vitals` at 08:30 → sees memory panel summarizing overnight trajectory, top consumers, threshold crossings; no drill-down needed for healthy nights
2. Drill-down — Eric sees WARN/CRITICAL on memory panel → runs `/vitals --memory` → gets hourly buckets, top-5 process histogram, commit-vs-pagefile-budget line
3. Mid-incident — live thrash occurs → Eric runs `/vitals --memory --since=-2h` → sees the last 60 sample ticks inline (no CIM call, non-hanging)
4. RCA — post-incident, Eric greps `memory_timeseries.jsonl` for the failure window → has actual within-window data points, not just endpoints (rule R1 enables HIGH-confidence RCA)
5. Context-file heatmap — Eric runs `/vitals --context-files` → sees which `.md` files were read most across recent sessions (drives context-routing optimization)

## FUNCTIONAL REQUIREMENTS

- **FR-001** — `tools/scripts/memory_sampler.py` emits one JSONL line per invocation to `data/logs/memory_timeseries.jsonl` with fields: `ts` (ISO-8601 UTC), `commit_bytes_sum`, `pagefile_free_gb`, `ram_free_gb`, `top5_procs` (list of `{name, pid, paged_mb}` ordered by `PagedMemorySize` desc)
- **FR-002** — `commit_bytes_sum` is sourced from `(Get-Process | Measure-Object PagedMemorySize -Sum).Sum` invoked via `powershell -NoProfile -Command` — no CIM, no WMI, no `Get-Counter` reference in the sampler hot path
- **FR-003** — Two scheduled tasks drive the sampler: `Jarvis-MemorySampler-Night` (every 2 min, active 22:00–08:00) and `Jarvis-MemorySampler-Day` (every 10 min, active 08:00–22:00) — registered via `tools/scripts/register_memory_sampler_tasks.ps1`
- **FR-004** — `tools/scripts/verify_sampler_coverage.py` computes tick completion rate over a window (default last 24 h) and exits 1 if any contiguous gap exceeds 2× its expected cadence (i.e. >20 min overnight or >4 min equivalent; configurable via CLI)
- **FR-005** — `hook_events.py` records Read-tool `file_path` values (whitelist: only the `file_path` string, nothing else) into a new sidecar field so `/vitals --context-files` can aggregate load counts per `.md` path across recent sessions
- **FR-006** — `/vitals` default output gains a **Memory** block summarizing: peak `commit_bytes_sum` in last 24 h, peak/pagefile-budget ratio, top-1 consumer at peak, tick completion rate, WARN threshold (peak > 70% of pagefile-allocated) / CRITICAL (peak > 90%)
- **FR-007** — `/vitals --memory` produces a detailed panel: hourly buckets (max/avg per bucket) for last 24 h, top-5 consumer histogram across the window, pagefile/RAM free line, any ticks where `commit_bytes_sum > pagefile_allocated_bytes` flagged as over-commit crossings
- **FR-008** — `/vitals --context-files` aggregates Read-tool file-path counts from `hook_events.py` log across the last 7 days, output as a count-ranked list limited to `.md` files (heatmap-style ranking, top 20)
- **FR-009** — `/vitals --token-costs` and `/vitals --reaper-log` flags exist and print the literal line `"not yet available — blocked on [dependency]"` with a stable exit code 0 (stub so dashboards wiring to these flags do not break when the dependencies ship)
- **FR-010** — `vitals_collector.py` output schema gains a `memory` section plus a non-bumping minor version (e.g. `1.1.0`); consumers of `1.0.0` continue to work (backward-compatible additive change)

## NON-FUNCTIONAL REQUIREMENTS

- **Platform** — Windows-only (PowerShell one-shot per tick via `subprocess.run` with explicit args list, no `shell=True` per PRD-1 orphan-prevention policy)
- **Performance** — Each sampler tick completes under 2 seconds wall clock on an idle system; tick never calls CIM, WMI, or `Get-Counter`
- **Storage** — JSONL grows ~8.6K lines/day (night 2-min × 10 h = 300 + day 10-min × 14 h = 84 → ~384/day actual; ~50 MB/year uncompressed); no retention in v1, rotation deferred
- **Failure mode** — A failed tick writes nothing (no partial lines, no dummy records); completion rate ISC surfaces tick loss
- **Reversibility** — Disabling both scheduled tasks and deleting `memory_sampler.py` removes the sampler entirely; no other files depend on `memory_timeseries.jsonl` for non-observability functions

## ACCEPTANCE CRITERIA

### Phase 1: Sampler + schedule

- [x] `tools/scripts/memory_sampler.py` exists and is invokable as `python tools/scripts/memory_sampler.py` with no args, appending exactly one line to `data/logs/memory_timeseries.jsonl` per invocation | Verify: Test — run once, assert file grows by exactly 1 line and JSON parses with all required fields | model: sonnet |
- [x] Every JSONL line contains the required keys `ts`, `commit_bytes_sum`, `pagefile_free_gb`, `ram_free_gb`, `top5_procs` with non-null values | Verify: Custom — `python tools/scripts/verify_sampler_schema.py` reads last 10 lines, exits 1 if any key missing or null | model: sonnet |
- [x] Both scheduled tasks `Jarvis-MemorySampler-Night` and `Jarvis-MemorySampler-Day` are registered with correct triggers and MultipleInstances=IgnoreNew | Verify: `schtasks /query /tn "Jarvis-MemorySampler-Night" /v /fo LIST` and day equivalent — both return active schedules matching the documented cadence | model: haiku |
- [x] **Anti-criterion**: Sampler source contains zero occurrences of `CimInstance`, `WmiObject`, `Get-Counter`, or `Win32_` class names | Verify: `grep -En "CimInstance|WmiObject|Get-Counter|Win32_" tools/scripts/memory_sampler.py` exits non-zero with empty output | model: haiku |

### Phase 2: Coverage verifier

- [x] `tools/scripts/verify_sampler_coverage.py` computes tick completion rate and identifies contiguous gaps | Verify: Test — unit test feeds synthetic JSONL with a 25-min night gap; verifier exits 1 and names the gap window | model: sonnet |
- [ ] After 48 h of continuous sampling, tick completion rate is ≥95% when measured against the time-of-day cadence schedule | Verify: Custom — `python tools/scripts/verify_sampler_coverage.py --window 48h --min-rate 0.95` exits 0 | model: sonnet | STATUS: BUILT-UNVALIDATED — window 2026-04-20T22:00 ET |
- [x] The verifier counts tick-loss during known observed pressure events separately (any tick gap within a window where `commit_bytes_sum > 70%` of pagefile budget is flagged as a pressure-gap) | Verify: Read — inspect verifier output for a `pressure_gaps[]` key populated from the most recent sampling window | model: sonnet |

### Phase 3: Hook instrumentation

- [x] `tools/scripts/hook_events.py` records Read-tool `file_path` into each PostToolUse event (whitelist: only `tool=="Read"` AND only the `file_path` string captured) | Verify: Test — unit test sends a simulated Read PostToolUse payload, asserts written JSONL contains `file_path` and no other input fields | model: sonnet |
- [x] **Anti-criterion**: No tool other than `Read` has its `file_path` / input contents captured — all other tools continue to record only `input_len` per existing schema | Verify: Test — assert Bash PostToolUse event contains no `file_path` or `command` field | model: sonnet |

### Phase 4: /vitals integration

- [ ] `/vitals` default terminal output contains a `MEMORY:` block with peak, ratio, top-1 consumer, and tick completion rate | Verify: Test — run `python tools/scripts/vitals_collector.py --pretty` and assert top-level `memory` key with required sub-fields | model: sonnet |
- [ ] `/vitals --memory` returns hourly-bucketed commit data for last 24 h plus top-5 consumer histogram plus flagged over-commit crossings | Verify: Review — invoke `/vitals --memory` on real data, confirm all three sections render with non-empty values when data exists | model: sonnet |
- [ ] `/vitals --context-files` outputs a count-ranked list of `.md` files from the last 7 days of hook_events data, limited to top 20 | Verify: Test — feed synthetic hook_events JSONL with 25 distinct `.md` paths, assert output has exactly 20 entries ordered by count desc | model: sonnet |
- [ ] `/vitals --token-costs` and `/vitals --reaper-log` both print exactly the line `not yet available — blocked on [dependency]` with exit code 0 | Verify: Test — invoke each flag, assert stdout matches regex and exit code is 0 | model: sonnet |
- [x] `vitals_collector.py` output `_schema_version` is `1.1.0` and the `1.0.0` top-level key set is still present (additive-only change) | Verify: Custom — `python tools/scripts/verify_vitals_schema.py --compat 1.0.0` exits 1 if any 1.0.0 key is missing or renamed | model: sonnet |

### Phase 5: Cross-cutting anti-criteria

- [x] **Anti-criterion**: No PRD-2-shipped code issues overnight Slack alerts (`slack_notify.notify` call) for memory pressure; only `/vitals` morning brief surfaces the signal | Verify: `grep -rEn "slack_notify|slack_send" tools/scripts/memory_sampler.py tools/scripts/verify_sampler_coverage.py` exits non-zero with empty output | model: haiku |
- [x] **Anti-criterion**: Sampler hot path never invokes Python `subprocess.run` with `shell=True` (consistency with PRD-1 orphan-prevention policy) | Verify: `grep -En "shell=True" tools/scripts/memory_sampler.py` exits non-zero with empty output | model: haiku |

**ISC Quality Gate: PASS (6/6)** — 16 criteria across 5 phases (≤8 per phase ✓); single-sentence, state-not-action ✓; binary pass/fail ✓; 4 anti-criteria ✓; every criterion has `| Verify:` suffix ✓; vacuous-truth guards present (custom verifiers exit 1 on absent data; anti-criteria name explicit forbidden strings; verify commands target the primary data source named in the criterion text — e.g. completion-rate criterion reads `memory_timeseries.jsonl` which is the artifact the criterion describes).

## SUCCESS METRICS

- **Primary** — Tick completion rate ≥95% over any rolling 7-day window, verified by `verify_sampler_coverage.py`
- **Leading indicator** — At least one observed WARN-threshold crossing (commit > 70% of pagefile budget) is captured with within-window data points before the next incident, enabling a MEDIUM-or-higher confidence RCA per rule R1
- **Secondary** — `/vitals` morning brief surfaces an interpretable memory panel without user drill-down 90%+ of days (panel renders with non-empty data)
- **Qualitative** — Post-incident RCA documents written after PRD-2 ships cite `memory_timeseries.jsonl` as the primary evidence source, not endpoint-only heartbeat duration

## OUT OF SCOPE

- Windows Service conversion (deferred to v2 if tick-loss during pressure events is observed; upgrade trigger defined in RISKS R1)
- JSONL retention/rotation (file stays append-only in v1; rotation backlog item)
- Live token-cost panel (blocked on Claude Code Stop-hook exposing token data — `hook_session_cost.py` infrastructure already exists, returns all-null today)
- Reaper log panel (blocked on out-of-band reaper existing — separate backlog)
- Backfilling heartbeat-duration proxy into a historical memory series
- Automatic remediation on threshold crossing (observation-only v1)

## DEPENDENCIES AND INTEGRATIONS

- **PowerShell** — one-shot `powershell -NoProfile -Command` per tick (no interactive shell, no profile load)
- **Windows Task Scheduler** — two new tasks (`Jarvis-MemorySampler-Night`, `Jarvis-MemorySampler-Day`) registered via `register_memory_sampler_tasks.ps1`
- **`tools/scripts/hook_events.py`** — FR-005 extends this file; coordinated with Claude Code hook lifecycle
- **`tools/scripts/vitals_collector.py`** — FR-010 adds a `memory` section; schema bump to 1.1.0
- **`.claude/skills/vitals/SKILL.md`** — updated to document new flags and memory panel (documentation change, not a dependency blocker)
- **pywin32 (indirect)** — not required by this PRD (sampler uses `subprocess` + PowerShell, not win32 API); mentioned only to disclaim dependency

## RISKS AND ASSUMPTIONS

### Risks

- **R1 — Scheduled-task tick loss during severe memory pressure**: Fresh `python.exe` cold-start can fail with WinError 1455 when interpreter heap init cannot allocate (exactly the 2026-04-18 incident). A resident Windows Service would not suffer this. **Mitigation**: ISC explicitly measures tick completion rate during pressure events (`pressure_gaps[]`); if any real incident shows >20% tick loss during pressure, upgrade to service in a v2 PRD (sampling logic stays identical, only lifecycle wrapper changes). Post-PRD-1 pagefile increase to 64 GB (commit limit 137 GB) substantially raises the pressure floor before this failure mode activates.
- **R2 — `Get-Process` returns zero or partial results under extreme pressure**: unlike CIM, this has not been observed to hang but could silently return incomplete data. **Mitigation**: sampler logs a non-null sentinel even on partial results; verifier flags any tick where `commit_bytes_sum < 1 GB` on a system that normally runs >10 GB as suspect.
- **R3 — `hook_events.py` whitelist for Read `file_path` creates a precedent**: future maintainers might extend the whitelist to capture other tool inputs, recreating the secret-leak risk the current design explicitly avoids. **Mitigation**: FR-005 anti-criterion explicitly asserts only `Read.file_path` is captured; regression test enforces this.
- **R4 — `/vitals --context-files` reveals memory-index content patterns**: file-path heatmap exposes which knowledge areas Eric reads most — low sensitivity but worth noting. **Mitigation**: paths are gitignored in existing layout; heatmap output is local-only (no Slack).
- **R5 — Schema 1.1.0 additive-change drift**: future consumers may start requiring the new `memory` key and break the 1.0.0 compat claim. **Mitigation**: FR-010 verifier script explicitly checks 1.0.0 key set is still present; runs in CI-equivalent.

### Assumptions

- Eric reboots once after scheduled tasks register; otherwise new tasks inherit current logon session state normally via Task Scheduler
- 64 GB pagefile (PRD-1 pre-req) is already applied; R1 mitigation quality depends on this being true
- `hook_events.py` modifications do not require coordinating with Claude Code version upgrades (hook payload schema is stable)
- `/vitals` skill surface accepts CLI flags via a thin argparse layer the SKILL.md can reference (no SKILL.md runtime parsing — the flags are passed to `vitals_collector.py` or a sibling script)
- PRD-1 ships before PRD-2 begins BUILD so the orphan-prevention patterns (no `shell=True`, no `for /f today.py`) are already policy when memory_sampler.py is authored

## OPEN QUESTIONS

- **OQ1** — Does `/vitals` skill currently support passing argv to `vitals_collector.py`, or does the skill parse flags in Markdown? Need to confirm during BUILD kickoff; if the latter, FR-006–FR-009 need a thin Python front-end.
- **OQ2** — Should the sampler also record per-tick `claude.exe` count and `python.exe` count as named fields (beyond top-5 aggregation)? Recommendation: yes — cheap, directly answers the recurring "how many claude/python are live" question. Defer decision to BUILD.
- **OQ3** — Retention policy: 90-day? 30-day with weekly aggregate? Currently append-only. Defer to a retention PRD once file size exceeds 100 MB (projected ~2 years).
- **OQ4** — Should FR-009 stub flags emit a TELEMETRY event when invoked, so Eric's usage of yet-unavailable flags surfaces as a priority signal for unblocking? Low effort, possibly valuable — defer to BUILD.

## NEXT STEP

Ship PRD-1 first (orphan-prevention). Then run `/implement-prd memory/work/memory-observability/PRD.md` to execute the full BUILD → VERIFY → LEARN loop. Execution order within PRD-2: sampler + schedule → coverage verifier → hook_events extension → /vitals panel + flags → schema verifier.
