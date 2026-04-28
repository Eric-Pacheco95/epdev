# Overnight Run Report — codebase_health — 2026-04-28

**Branch:** jarvis/overnight-2026-04-28  
**Dimension:** codebase_health  
**Goal:** Improve test coverage in tools/scripts/**/*.py  
**Metric:** pytest passed count  
**Guard:** flake8 fatal errors (E9, F63, F7, F82) == 0

## Summary

| | |
|---|---|
| Baseline | 2654 |
| Final | 2939 |
| Net gain | +285 |
| Iterations kept | 19 |
| Iterations discarded | 1 (import path fix — no metric change) |
| No-improvement streak max | 1 (stop threshold was 5) |
| Guard failures | 0 |

## Run Log (TSV)

```
iter	commit	description	before	after	delta	kept
1	6932b6a	test(update_status): 30 tests for pure helpers	2654	2684	+30	yes
2	5d6e710	test(sync_handoff): 22 tests for pure helpers	2684	2706	+22	yes
3	620479e	test(check_autonomy_map): 18 tests	2706	2724	+18	yes
4	fc21756	test(followon_pending): expand to 16 tests	2724	2740	+16	yes
5	6a52e7d	test(task_proposals): 17 tests	2740	2757	+17	yes
6	4666de0	test(costs_aggregator): 9 build_window tests	2757	2766	+9	yes
7	ecb57c5	test(jarvis_autoresearch): 9 tests	2766	2775	+9	yes
8	fc48c7c	fix(test_collectors_core): sys.path fix (no metric change)	2775	2775	0	no
9	6564af4	test(hook_stop): 4 tests for _update_signal_count	2771	2775	+4	yes
10	b351edc	test(compress_signals): 12 tests	2775	2787	+12	yes
11	b499c1f	test(morning_briefing): 4 tests for _proposal_pending	2787	2791	+4	yes
12	daaf807	test(isc_validator): 36 tests for pure helpers	2791	2827	+36	yes
13	ced1af0	test(isc_producer): 20 tests	2827	2847	+20	yes
14	768dacb	test(vitals_collector): 26 tests	2847	2873	+26	yes
15	d6d99be	test(vitals_collector): 13 more tests	2873	2886	+13	yes
16	ac64e73	test(lib/backlog): 10 edge-case tests	2886	2896	+10	yes
17	2494bdd	test(collectors/backlog_health): 12 tests	2896	2908	+12	yes
18	dc55a87	test(hook_post_compact): 7 tests	2908	2915	+7	yes
19	11ed610	test(jarvis_dispatcher): 8 tests for sweep_pending_review	2915	2923	+8	yes
20	78763b1	test(jarvis_autoresearch): 16 tests for _safe_telos_proposal/_grep_anchor	2923	2939	+16	yes
```

## Files Modified / Created

### New test files
- `tests/test_update_status.py` (30 tests)
- `tests/test_sync_handoff.py` (22 tests)
- `tests/test_check_autonomy_map.py` (18 tests)
- `tests/test_task_proposals_lib.py` (17 tests)
- `tests/test_isc_validator_pure.py` (36 tests)
- `tests/test_isc_producer.py` (20 tests)
- `tests/test_vitals_collector_pure.py` (39 tests)
- `tests/test_collectors_backlog_health.py` (12 tests)

### Expanded test files
- `tests/test_followon_pending.py` (+12 tests)
- `tests/test_costs_aggregator.py` (+9 tests)
- `tests/test_jarvis_autoresearch.py` (+25 tests)
- `tests/test_hook_stop.py` (+4 tests)
- `tests/test_compress_signals.py` (+12 tests)
- `tests/test_morning_briefing.py` (+4 tests)
- `tests/test_lib_backlog.py` (+10 tests)
- `tests/test_hook_post_compact.py` (+7 tests)
- `tests/test_jarvis_dispatcher.py` (+8 tests)

### Fixed test file
- `tests/test_collectors_core.py` (sys.path fix for standalone execution)

## Strategy

Targeted untested pure helper functions — no subprocess, no external I/O — using `tmp_path`, `monkeypatch`, and `unittest.mock.patch.object` to redirect module-level path constants.

Key findings:
- `isc_validator.py` had 20+ pure functions with zero test coverage; 36 tests added in one iteration
- `vitals_collector.py` had isolated helpers (_summarize_overnight_log, build_memory_summary, compute_trend_averages) fully testable in 2 iterations
- Naming collision: `tests/test_isc_validator.py` conflicted with `tests/defensive/test_isc_validator.py`; resolved by renaming to `test_isc_validator_pure.py`
- One no-improvement iteration: import path fix for test_collectors_core.py (tests ran via pytest path leakage in full suite)
