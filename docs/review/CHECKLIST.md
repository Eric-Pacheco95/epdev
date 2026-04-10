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
| 1 | B1 | todo | Claude | Archive path traversal hardening |  |  |  |  |
| 2 | B1 | todo | Claude | Run-report path/boundary hardening |  |  |  |  |
| 3 | B1 | todo | Claude | Verifier fail-closed enforcement |  |  |  |  |
| 4 | B1 | todo | Claude | Dispatcher livelock prevention for non-executable verify |  |  |  |  |
| 5 | B2 | todo | Claude | Backlog reader robustness |  |  |  |  |
| 6 | B2 | todo | Claude | Context-file path/secret bypass closure |  |  |  |  |
| 7 | B2 | todo | Claude | Follow-on state/throttle correctness |  |  |  |  |
| 8 | B2 | todo | Claude | Routine injection starvation/cadence fixes |  |  |  |  |
| 9 | B2 | todo | Claude | Hook-events malformed-input fail-closed |  |  |  |  |
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
