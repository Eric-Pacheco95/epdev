# Review Checklist

Use with `docs/review/REVIEW.md`.

## Status values

- `todo`
- `in_progress`
- `fixed`
- `partial`
- `blocked`
- `repro_mismatch`
- `accepted_risk`

## Batch prompt template

`Read docs/review/REVIEW.md and docs/review/CHECKLIST.md. Work only batch <Bx> (3-5 items). For each item: run repro first, then implement fix, then rerun verify plus related regressions. Update this checklist row with status and evidence paths.`

## Items

| id | batch | status | owner | title | before_evidence | after_evidence | regression_evidence | notes |
|---|---|---|---|---|---|---|---|---|
| 1 | B1 | fixed | Claude | Archive path traversal hardening | jarvis_dispatcher.py:478, 1860; backlog.py:141 raw task_id, no allowlist | backlog.py validate_task() id allowlist `^[A-Za-z0-9_\-.]+$`; jarvis_dispatcher.py `_safe_filename_component()` helper + resolve/bound checks in archive_expired_pending_review() and save_run_report() | 26/26 dispatcher self-tests pass | Trust boundary low risk but real architectural gap; fixed defensively |
| 2 | B1 | fixed | Claude | Run-report path/boundary hardening | save_run_report() line 1860 (%Y%m%d_%H%M%S, no path containment) | Filename now `%Y%m%d_%H%M%S_%f` (microsecond); explicit path= containment check against RUNS_DIR | 26/26 dispatcher self-tests pass | Latent only — no current attacker path |
| 3 | B1 | fixed | Claude | Verifier fail-closed enforcement | verify_5e1/5e2_falsification.py exit 0 on all-SKIP; 5E-1 I6 raw `created` grouping; 5E-2 I8 dead `reports` param | Both: FALSIFICATION_WINDOW_DATE + post-window pass_count==0 → FAIL. 5E-1: `_to_calendar_day()` normalizes timestamps. 5E-2 I8: full backlog+archive task_index cross-reference, counts follow-on completions per calendar day | Pre-window today both exit 0; synthetic post-window 5E-1 exits 1 | I8 now fully wired (no TODO stub) |
| 4 | B1 | fixed | Claude | Dispatcher livelock prevention for non-executable verify | jarvis_dispatcher.py:2228 dirty-tree returns "continue" with status=pending → infinite spin; select_next_task() silently skips no-ISC tasks | Inline-refused → status=manual_review, failure_type=dirty_tree_blocked. select_next_task(): no-verifiable-ISC → manual_review (failure_type=no_verifiable_isc); blocked-command ISC → manual_review (failure_type=isc_blocked_command) | 26/26 dispatcher self-tests pass | Active production risk (backlog file dirties tree) — highest priority of B1 |
| 5 | B2 | fixed | Claude | Backlog reader robustness | read_backlog() L198 no try/except → JSONDecodeError crash; deliverable_exists() L303 KeyError on missing id; backlog_append dedups by routine_id only | read_backlog() per-line try/except + quarantine to data/backlog_quarantine.jsonl; deliverable_exists() guards missing id; select_next_task() escalates missing-id → manual_review/missing_id; backlog_append() rejects duplicate caller-supplied id with stderr warning | 26/26 dispatcher self-tests pass; 5a smoke parsed 1/1 valid + quarantine written; 5c smoke second-id returns None | 5c production duplicates already gone; write-time check added as defense-in-depth |
| 6 | B2 | fixed | Claude | Context-file path/secret bypass closure | regex char-class bug `[/\\]\|$` (literal $); .env.local/.env.production/credentials.json/ trailing-slash bypass; Glob/Grep had no validator path; _check_autonomous_file_containment used naive startswith; fail-open when JARVIS_WORKTREE_ROOT unset | _is_secret_path() helper with basename normalization (.env*, credential*, secret*, .key/.pem variants); regex `(?:[/\\]\|$)` fix; explicit Glob/Grep handler with secret + containment checks; Path.is_relative_to() containment; fail-closed on Write/Edit when worktree unset | 26/26 self-tests pass; 15/15 secret-path smoke; Glob `.env`+`.env.local` blocked, README.md allowed | Highest-reachability item — autonomous workers can no longer exfil secrets via Grep |
| 7 | B2 | fixed | Claude | Follow-on state/throttle correctness | _record_followon_emission no lock → 750/1000 lost under 4x250 stress; non-int count crashes throttle; negative count bypasses; routine_state TypeError unhandled; dedup-skip advances last_injected | New lib/file_lock.py (locked_append + locked_read_modify_write); _record_followon_emission uses locked_rmw with negative-clamp mutator; _load_followon_state type validation; _followon_throttle_ok clamps; (ValueError, TypeError) catch + isinstance guard; last_injected only updated on successful injection | 26/26 self-tests pass; 4-thread stress 40/40 increments correct | lib/file_lock.py is now shared across followon, hook_events, hook_session_cost |
| 8 | B2 | fixed | Claude | Routine injection starvation/cadence fixes | inject_routines called after empty-backlog early return; schedule.type read NOWHERE; non-int interval_days crashes pass; one bad routine starves all (no per-routine try/except); unknown condition type fails open; interval_days=0/-5 reinject same day | _validate_routine_schema() pre-flight (id type, interval_days int≥1, schedule.type enum, condition.type enum); per-routine try/except wrapper; inject_routines moved before empty-backlog early return + re-read backlog; _eval_routine_condition unknown-type → fail closed | 26/26 self-tests pass | 8c-h converged to one schema validator + per-routine try/except |
| 9 | B2 | fixed | Claude | Hook-events malformed-input fail-closed | hook_events.py JSONDecodeError + bare pass → success=true empty-tool record + no lock (1-5 lines lost per 1000); hook_session_cost.py same parse fail-open; vitals_collector counts empty-session rows in totals | hook_events: parse_error row + sys.exit(1) + locked_append; hook_session_cost: parse_error row + exit(1) + write_cost_record consolidated to locked_append (msvcrt block deleted); vitals_collector skips empty session_id rows from total_sessions/daily_counts | 8x10 thread stress: 80/80 lines written, 0 dropped; both hooks exit 1 on malformed stdin | hook_session_cost lock pattern now lives in lib/file_lock.py only |
| 10 | B3 | todo | Claude | Hook command portability |  |  |  |  |
| 11 | B3 | todo | Claude | Validator schema normalization (`tool`/`tool_name`) |  |  |  |  |
| 12 | B3 | todo | Claude | Secret/file protections for all file-addressing tools |  |  |  |  |
| 13 | B3 | todo | Claude | Autonomous fail-closed without worktree root |  |  |  |  |
| 14 | B3 | todo | Claude | cp1252 output hardening |  |  |  |  |
| 15 | B4 | todo | Claude | Rate-limit exit-0 handling alignment |  |  |  |  |
| 16 | B4 | todo | Claude | Deliverable false-closure logic fix |  |  |  |  |
| 17 | B4 | todo | Claude | Empty-backlog/dirty-tree dispatcher behavior |  |  |  |  |
| 18 | B4 | todo | Claude | Duplicate backlog ID integrity + migration |  |  |  |  |
| 19 | B4 | todo | Claude | Query/events failure fidelity |  |  |  |  |
| 20 | B5 | todo | Claude | Secret scanner pattern refresh |  |  |  |  |
| 21 | B5 | todo | Claude | Defensive test rehab |  |  |  |  |
| 22 | B5 | todo | Claude | Hardcoded path/root-dir cleanup |  |  |  |  |
| 23 | B5 | todo | Claude | Scheduler wrapper exit-code propagation |  |  |  |  |
| 24 | B5 | todo | Claude | Retry event/notification semantics |  |  |  |  |
| 25 | B6 | todo | Claude | Archive overwrite prevention (duplicate IDs) |  |  |  |  |
| 26 | B6 | todo | Claude | Hook-event schema contract stabilization |  |  |  |  |
| 27 | B6 | todo | Claude | Backlog warning flood reduction |  |  |  |  |
| 28 | B6 | todo | Claude | `branch_lifecycle --help` behavior fix |  |  |  |  |
| 29 | B6 | todo | Claude | Analyzer noise baseline management |  |  |  |  |
| 30 | B6 | todo | Claude | Data-boundary policy alignment |  |  |  |  |
| 31 | B7 | todo | Claude | Windows `.cmd` Claude launcher compatibility |  |  |  |  |
| 32 | B7 | todo | Claude | Node destructive inline command validator coverage |  |  |  |  |
| 33 | B7 | todo | Claude | Weekly-synthesis template/backlog ISC parity |  |  |  |  |
| 34 | B7 | todo | Claude | Remove dangerous permissions skip in Slack poller |  |  |  |  |
| 35 | B8 | todo | Claude | Trust-topology pytest collection fix |  |  |  |  |
| 36 | B8 | todo | Claude | `hook_session_cost` malformed-input handling |  |  |  |  |
| 37 | B8 | todo | Claude | Verify-command admission gate automation |  |  |  |  |
| 38 | B8 | todo | Claude | Static-only gap closure runbook |  |  |  |  |
