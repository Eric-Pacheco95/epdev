# EPDEV Review Execution Pack

This tracked review document is intended for remote/SSH Claude Code sessions.

- Source context was produced during a deep audit harness run.
- Canonical local scratch logs remain in `_codex_scratch/REVIEW.md`.
- This file is the execution-ready queue and prioritization artifact.

## How To Use

1. Read this file and `docs/review/CHECKLIST.md`.
2. Work in batches of 3-5 items max.
3. For each item: repro first -> fix -> verify -> regression checks.
4. Update checklist evidence paths and status before moving on.

## Priority Order

Execute in this order:

1. Security boundaries and traversal risks
2. Verifier fail-closed behavior
3. Dispatcher liveness and crash integrity
4. Routine/follow-on state correctness
5. Telemetry correctness
6. Platform and long-tail cleanup

## Action Queue

### Batch B1

1. Harden archive path writes against traversal/absolute escape.
2. Harden run-report path generation and explicit save path boundary.
3. Make falsification verifiers fail closed on malformed/missing evidence.
4. Stop dispatcher livelock for permanently non-executable verify criteria.

### Batch B2

5. Make backlog readers robust to malformed rows and missing required fields.
6. Close context-file path and secret suffix bypasses.
7. Stabilize follow-on throttle state under malformed data and concurrency.
8. Harden routine injection to avoid starvation and degenerate cadence.
9. Make hook-events parser fail closed on malformed stdin.

### Batch B3

10. Fix hook command portability across hosts/shells.
11. Close autonomous validator schema mismatch (`tool` vs `tool_name`).
12. Extend secret/file protections to all file-addressing tools.
13. Fail closed in autonomous mode when worktree root is unset.
14. Fix Windows cp1252 output hazards.

### Batch B4

15. Address rate-limit exit-0 handling gaps in Claude consumers.
16. Fix dispatcher branch/deliverable false-closure heuristics.
17. Fix routine injection behavior with empty backlog and dirty trees.
18. Enforce backlog ID integrity and schema migration guardrails.
19. Include dispatcher failures in health rollups.

### Batch B5

20. Refresh secret scanner patterns (including `sk-proj-*`).
21. Rehab non-runnable/insufficient defensive tests.
22. Eliminate stale hardcoded root paths in runtime configs/scripts.
23. Fix scheduler wrapper exit-code propagation.
24. Correct notifier/event semantics for retrying tasks.

### Batch B6

25. Prevent pending-review archive overwrites on duplicate IDs.
26. Enforce hook-event schema at write boundary.
27. Reduce backlog warning flood under load.
28. Fix `branch_lifecycle.py --help` CLI contract.
29. Triage analyzer noise and set scoped baselines.
30. Align repository data-boundary policy for `memory/history/data`.

### Batch B7

31. Fix Windows worker subprocess launcher portability for Claude.
32. Close Node inline destructive-command miss in Bash validator.
33. Resolve weekly-synthesis template vs active backlog ISC drift.
34. Remove dangerous permissions bypass in Slack poller.

### Batch B8

35. Fix trust-topology pytest collection crash explicitly.
36. Make `hook_session_cost` malformed-input handling telemetry-safe.
37. Automate backlog/routine verify-command hygiene admission gate.
38. Close static-only audit gaps with an executable runbook.

## Done Criteria

A review item is complete only when:

- repro probe fails before change,
- fix is implemented,
- listed verify probes pass after change,
- related domain regressions are rerun,
- checklist status is updated with evidence artifact paths.
