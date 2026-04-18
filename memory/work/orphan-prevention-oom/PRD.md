---
slug: orphan-prevention-oom
created: 2026-04-18
status: draft
priority: P1
phase: PLAN
parent-incident: 2026-04-18 Python.exe orphan leak (9,488 zombies at 99.3% commit)
related-prds: memory/work/memory-observability/PRD.md (PRD-2, ships after)
context-sources:
  - history/decisions/2026-04-18-arch-review-oom-fix-v2.md
  - memory/learning/signals/2026-04-18_arch-review-oom-fix-v2.md
  - memory/work/_overnight-oom-2026-04-18/PYTHON_LEAK_TRIAGE.md
  - memory/work/_overnight-oom-2026-04-18/SESSION_TRIAGE_HANDOFF.md
---

# PRD: Orphan python.exe Prevention — Root-Cause Fix

## OVERVIEW

Eliminate the three architectural spawn patterns that leak orphaned `python.exe` processes on Windows, each of which survives its parent's termination because Windows does not cascade `TerminateProcess` to grandchildren. The 2026-04-18 OOM incident surfaced 9,488 orphaned `python.exe` processes (all dead PPIDs, count=1 each) driving 119.69 GB commit on a 32 GB RAM + 86 GB pagefile box. Triage isolated three spawn mechanisms: `shell=True` in `isc_executor.py`, `for /f ... today.py` in every `.bat` wrapper, and un-jobbed `subprocess.run([claude.exe, ...])` in three callers whose hooks spawn python.exe grandchildren. This PRD ships each fix sequenced by confirmed orphan rate (highest first), with no backwards-compat retention.

## PROBLEM AND GOALS

- Stop the recurring orphan-python.exe leak that caused the 2026-04-18 OOM (architectural, not transient)
- Remove all three confirmed spawn mechanisms at the code level — not add a reaper to mop up after them
- Keep success evidence standalone-verifiable so PRD-1 can be declared done before PRD-2 sampler ships
- Preserve current functional behavior of ISC verify, date-stamped log naming, and claude -p subprocess kill-on-timeout

## NON-GOALS

- Commit-pressure sampler and `/vitals` memory panel (owned by PRD-2, parallel session)
- Out-of-band reaper for already-accumulated orphans (one-time cleanup, not a system primitive)
- SessionCleanup expansion to node.exe zombies (separate P3 from SESSION_TRIAGE_HANDOFF)
- Extending `isc_executor.py` with a verify-method allowlist (v2 scope, called out in file comment)

## USERS AND PERSONAS

- Eric (sole operator) — depends on Jarvis scheduled tasks not driving his machine to thrash
- Autonomous producers (isc_producer, overnight_runner, dispatcher, heartbeat, security-audit) — indirect users via their subprocess call sites

## USER JOURNEYS OR SCENARIOS

1. ISCProducer runs 02:00 → spawns 25 verify commands via `isc_executor.handle_test()` → 60s timeout on one → **post-fix**: only the target python.exe is killed, no cmd.exe intermediary exists
2. Heartbeat fires hourly → `.bat` wrapper needs today's date → **post-fix**: `set LOGDATE=%DATE:~10,4%-%DATE:~4,2%-%DATE:~7,2%` resolves inline with zero subprocess
3. overnight_runner hits 7200s timeout on `claude -p` → **post-fix**: Job Object termination cascades to every hook python.exe descendant in one syscall

## FUNCTIONAL REQUIREMENTS

- **FR-001** — `tools/scripts/isc_executor.py:220` invokes `subprocess.run` without `shell=True`; command is parsed into an explicit list (shlex-split or structured verify method) before dispatch
- **FR-002** — Verify methods that cannot be safely list-parsed (arbitrary compound shell constructs) route to `MANUAL` instead of silent `shell=True` execution
- **FR-003** — All `.bat` files under `tools/scripts/run_*.bat` resolve the log date via the native Windows token `%DATE:~10,4%-%DATE:~4,2%-%DATE:~7,2%` — no `for /f ... today.py` pattern remains
- **FR-004** — A new module `tools/scripts/lib/windows_job.py` exposes `run_with_job_object(cmd, timeout, **kwargs)` that wraps `subprocess.Popen`, assigns the child to a Job Object with `JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE`, and on timeout kills the job (cascading to all descendants)
- **FR-005** — `overnight_runner.py`, `jarvis_dispatcher.py`, and `self_diagnose_wrapper.py` invoke `claude.exe` exclusively via `run_with_job_object()` — no raw `subprocess.run([claude.exe, ...])` call sites remain in these three files
- **FR-006** — The three fixes ship as three sequential commits (not one bundle), in this order: isc_executor → .bat wrappers → Job Object wrapper + callers
- **FR-007** — No backwards-compat shim, flag, or fallback path exists for `shell=True` verify dispatch or the old `for /f today.py` pattern

## NON-FUNCTIONAL REQUIREMENTS

- **Platform** — Windows-only (pywin32 is present at `C:\Users\ericp\AppData\Local\Programs\Python\Python312`; Job Object primitives require Windows)
- **Dependencies** — pywin32 must remain a declared/verified dependency of the repo (not a silent implicit one)
- **Reversibility** — Each of the three commits is independently revertable without touching the other two
- **Observability (carried, not introduced)** — Existing heartbeat + ISC logs continue to capture verify-method results; this PRD adds no new continuous instrumentation (that is PRD-2's scope)

## ACCEPTANCE CRITERIA

### Phase 1: Ship FR-001 / FR-002 (isc_executor)

- [ ] No occurrence of `shell=True` remains in `tools/scripts/isc_executor.py` | Verify: `grep -n "shell=True" tools/scripts/isc_executor.py` exits non-zero with empty output | model: haiku |
- [ ] Verify methods whose body cannot be shlex-split route to `MANUAL` with a recorded reason, not to silent shell dispatch | Verify: Test — unit test in `tests/defensive/test_isc_executor_no_shell.py` asserts shlex-unparseable input returns `MANUAL` status | model: sonnet |
- [ ] `handle_test()` spawns at most one process per verify call (the target command itself, no cmd.exe intermediary) | Verify: Test — unit test asserts `subprocess.run` is called with a list and `shell` is absent or False | model: sonnet |
- [ ] ISCProducer 02:00 run completes with the same pass/fail outcome distribution as the 7-day pre-fix baseline (±2 criteria drift) | Verify: Review — compare `data/logs/isc_producer_*.log` pre/post for first post-ship run | model: sonnet |

### Phase 2: Ship FR-003 (.bat wrappers)

- [ ] No `.bat` file under `tools/scripts/` contains the substring `for /f` with `today.py` on the same line | Verify: `grep -rn "for /f" tools/scripts/*.bat | grep -v "today.py" ; grep -rn "today.py" tools/scripts/*.bat` — second grep exits non-zero with empty output | model: haiku |
- [ ] Every `.bat` wrapper that writes a dated log uses `%DATE:~10,4%-%DATE:~4,2%-%DATE:~7,2%` for its date token | Verify: Custom — `python tools/scripts/verify_bat_date_tokens.py` iterates all `run_*.bat` and exits 1 if any log-named file uses a non-native date source | model: sonnet |
- [ ] First hourly heartbeat post-ship produces a correctly-named log file (e.g. `heartbeat_2026-MM-DD.log`) without spawning `today.py` | Verify: Test — run `tools/scripts/run_heartbeat.bat` in a sandboxed cmd; assert `heartbeat_*.log` matches today's date AND no `python.exe today.py` appears in Process Monitor trace during the run | model: sonnet |

### Phase 3: Ship FR-004 / FR-005 (Job Object wrapper + callers)

- [ ] `tools/scripts/lib/windows_job.py` exports `run_with_job_object(cmd, timeout, **kwargs)` returning a `CompletedProcess`-equivalent result | Verify: Read — inspect file; confirm signature, docstring, and use of `win32job.CreateJobObject` + `JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE` | model: sonnet |
- [ ] On timeout, `run_with_job_object()` terminates the Job Object such that all descendant PIDs (including hook python.exe grandchildren) exit within 5 seconds | Verify: Test — integration test in `tests/defensive/test_windows_job_cascade.py` spawns `cmd.exe /c python -c "import subprocess; subprocess.Popen(['python','-c','import time; time.sleep(300)'])"`, forces timeout, asserts grandchild PID is gone | model: sonnet |
- [ ] `overnight_runner.py`, `jarvis_dispatcher.py`, `self_diagnose_wrapper.py` contain zero direct `subprocess.run([claude` or `subprocess.Popen([claude` call sites | Verify: `grep -En "subprocess\.(run\|Popen)\(\[['\"]?claude" tools/scripts/overnight_runner.py tools/scripts/jarvis_dispatcher.py tools/scripts/self_diagnose_wrapper.py` exits non-zero with empty output | model: haiku |

### Phase 4: Post-ship success gate

- [ ] Daily snapshot `(Get-Process python -ErrorAction SilentlyContinue).Count` stays below 20 for 7 consecutive days after the third commit lands | Verify: Custom — new scheduled task `Jarvis-OrphanSnapshot` (00:05 daily) appends `{date, count}` to `data/logs/orphan_python_snapshot.jsonl`; `python tools/scripts/verify_orphan_streak.py` exits 1 if any of the last 7 entries has `count >= 20` or fewer than 7 entries exist | model: sonnet |
- [ ] **Anti-criterion**: No `.bat` wrapper, no callsite in the three target .py files, and no line in `isc_executor.py` introduces a new `shell=True` or `for /f ... python` pattern during or after the rollout | Verify: Custom — `python tools/scripts/verify_no_orphan_spawn_patterns.py` greps the three surface areas with explicit pattern list and exits 1 on any match (not filter-and-print) | model: sonnet |
- [ ] **Anti-criterion**: No `CompatShim`, `legacy_shell_true`, `_fallback_for_f`, or commented-out-old-path block survives in any shipped file | Verify: `grep -rEn "CompatShim|legacy_shell_true|_fallback_for_f|# OLD:" tools/scripts/ isc_executor.py` exits non-zero with empty output | model: haiku |

**ISC Quality Gate: PASS (6/6)** — 14 criteria across 4 phases (≤8 per phase ✓); single-sentence, state-not-action ✓; binary pass/fail ✓; 2 anti-criteria ✓; every criterion has `| Verify:` suffix ✓; vacuous-truth guards present (custom verifier scripts exit 1, `test -n` style greps, anti-criteria name explicit forbidden strings not wildcards, verify commands target the same primary data source named in the criterion text — e.g. the orphan-streak verifier reads `orphan_python_snapshot.jsonl` which is the artifact the criterion describes).

## SUCCESS METRICS

- **Primary** — Orphan `python.exe` count < 20 for 7 consecutive days post-third-commit (tracked via `orphan_python_snapshot.jsonl`)
- **Secondary** — No OOM preflight abort attributable to python-orphan commit pressure for 30 days post-ship
- **Leading indicator** — ISCProducer 02:00 run spawns exactly `N_criteria` `python.exe` processes (one per verify), not `2 * N_criteria` (which would indicate cmd.exe still intermediating)

## OUT OF SCOPE

- Reaping the existing 9,488 orphans (one-time cleanup via Eric-approved `Stop-Process` command, not this PRD's scope)
- Commit-pressure sampler and `/vitals` panel (PRD-2)
- SessionCleanup node.exe coverage (P3 from triage handoff)
- `claude_lock` PID-liveness + 30-min max hold (separate backlog item from arch-review side finding)
- pywin32 pinning in a requirements file (already present; verified in FR-004 acceptance)

## DEPENDENCIES AND INTEGRATIONS

- **pywin32** — `win32job`, `win32api`, `win32process`, `win32con` (verified installed)
- **Python 3.12** — `subprocess`, `shlex`
- **Windows Task Scheduler** — new task `Jarvis-OrphanSnapshot` for success-gate verification
- **Existing `tools/scripts/lib/` helpers pattern** — `worktree.py`, `net_util.py`, `file_lock.py` (architectural precedent for shared helpers)

## RISKS AND ASSUMPTIONS

### Risks

- **R1 — Verify-method regression**: moving `handle_test` off `shell=True` may break verify commands that rely on shell features (`&&`, `|`, env expansion). Mitigation: FR-002 routes unparseable commands to `MANUAL` with a recorded reason; first post-ship ISCProducer run is compared against 7-day baseline (acceptance criterion) to catch drift.
- **R2 — Job Object POC assumption**: assumes `JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE` + `TerminateJobObject` cascades to all descendants including those launched after assignment. Integration test in FR-004 acceptance validates this explicitly — must run locally before FR-005 call-site conversion.
- **R3 — `.bat` date-token fragility**: `%DATE:~10,4%-%DATE:~4,2%-%DATE:~7,2%` depends on the system's Short Date format being `MM/dd/yyyy`. Mitigation: FR-003 verification script includes a locale-probe step; if Short Date deviates, fall back to `powershell -NoProfile -Command "Get-Date -Format yyyy-MM-dd"` (a one-shot call that dies with its parent cmd since no grandchild is spawned).
- **R4 — Anti-criterion false positives**: grep-based anti-criterion for `shell=True` may flag legitimate future non-subprocess uses. Mitigation: anti-criterion is scoped to `tools/scripts/isc_executor.py` specifically, not the whole codebase.

### Assumptions

- Windows 11 Home on the target box; Job Object behavior matches documented semantics for this edition
- Eric reboots (or re-launches all schedulers) once after the third commit lands so existing orphan reservoirs begin draining via natural task cycling
- No hidden fourth mechanism exists — triage's PPID histogram showed all 9,488 orphans matched Mechanisms A/B/C (count=1 per PPID, no live spawner)

## OPEN QUESTIONS

- **OQ1** — Should FR-002 `MANUAL` routing emit a Slack signal or just log locally? Default: log-only (matches "no new continuous observability" NFR); Slack surfacing can piggyback on PRD-2's morning brief.
- **OQ2** — Is `JOB_OBJECT_LIMIT_BREAKAWAY_OK` needed, or does the default (deny breakaway) match intent? Intent: deny breakaway so hooks cannot escape; confirm during FR-004 integration test writing.
- **OQ3** — After PRD-2 ships, is the standalone `Jarvis-OrphanSnapshot` task deprecated or kept as a cheap independent check? Recommendation: keep as independent sentinel (different data source = defense-in-depth).

## NEXT STEP

Run `/implement-prd memory/work/orphan-prevention-oom/PRD.md` to execute the full BUILD → VERIFY → LEARN loop. Execution order is the three commits in FR-006 sequence.
