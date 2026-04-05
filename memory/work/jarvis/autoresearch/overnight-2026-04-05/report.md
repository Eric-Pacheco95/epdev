# Overnight Run Report — codebase_health — 2026-04-05

**Branch:** jarvis/overnight-2026-04-05  
**Dimension:** codebase_health  
**Scope:** tools/scripts/**/*.py  
**Goal:** Improve test coverage and fix warnings. Each iteration adds one test or fixes one issue.

## Summary

- **Baseline:** 588 passed, 2 failed
- **Final:** 775 passed, 0 failed
- **Delta:** +187 tests, +2 bug fixes
- **Kept:** 19 iterations (19 commits)
- **Discarded:** 1 iteration (iteration 6 attempt — removing unused imports did not improve metric)
- **Guard failures:** 0

## What Was Done

### Bug Fixes (2)
1. **test_collector_types_registry** - Added missing `producer_recency` to expected set.
2. **collect_file_recency (collectors/core.py)** - Clamped `days` to `max(0, days)` to prevent negative values on Windows NTFS.

### Import Fix (1)
- **test_collectors_prd_recency.py** - Changed bare `from collectors.core import ...` to fully-qualified path.

### New Test Files (17)

| File | Tests | Coverage Target |
|------|-------|----------------|
| test_manifest_db.py | 13 | manifest_db.py graceful fallback + write paths |
| test_hook_session_cost.py | 11 | _extract_token_data, build_cost_record |
| test_consolidate_overnight.py | 9 | generate_summary_md |
| test_hook_stop.py | 9 | _slugify, _unique_path |
| test_hook_post_compact.py | 6 | _unchecked_items |
| test_morning_feed.py | 11 | _clean_html, parse_discovered_sources |
| test_jarvis_dispatcher_helpers.py | 17 | all_deps_met, resolve_model, _scan_task_metadata_injection |
| test_jarvis_index_helpers.py | 9 | _parse_signal_frontmatter, _parse_producer_from_logname |
| test_security_scan_helpers.py | 9 | apply_false_positive_filter |
| test_slack_poller_parse.py | 7 | _parse_message |
| test_dream_helpers.py | 10 | _slug_from_theme, _infer_memory_type |
| test_research_producer_helpers.py | 9 | _domain_to_title, is_static_due |
| test_overnight_runner_helpers.py | 19 | next_dimension, dimensions_to_run, validate_command |
| test_overnight_runner_parse_program.py | 6 | parse_program |
| test_jarvis_dispatcher_context_files.py | 11 | validate_context_files |
| test_jarvis_dispatcher_sanitize.py | 11 | _sanitize_anti_pattern_message, _validate_profile_content |
| test_collect_sources.py | 13 | parse_frontmatter_date, parse_rating, safety_check |
| test_worktree_lock.py | 6 | acquire_claude_lock, release_claude_lock |

## TSV Run Log

iteration	commit_hash	metric_value	delta	status	description
1	ee3e5f9	590	+2	kept	Fix test_collector_types_registry: add producer_recency to expected set
2	dcccab8	590	+0	kept	Fix test_collectors_prd_recency import path (bare to fully-qualified)
3	7bf4fdd	601	+11	kept	Add test_manifest_db.py (13 tests)
4	b154a74	602	+1	kept	Fix collect_file_recency negative days clamping
5	2527389	613	+11	kept	Add test_hook_session_cost.py (11 tests)
6a	reverted	613	+0	discarded	Remove unused imports -- metric unchanged, reverted
6b	eb235d6	622	+9	kept	Add test_consolidate_overnight.py (9 tests)
7	7163b51	637	+15	kept	Add test_hook_stop.py + test_hook_post_compact.py (15 tests)
8	8c38c51	648	+11	kept	Add test_morning_feed.py (11 tests)
9	413f24d	665	+17	kept	Add test_jarvis_dispatcher_helpers.py (17 tests)
10	1e86563	684	+19	kept	Add test_overnight_runner_helpers.py (19 tests)
11	a03e193	693	+9	kept	Add test_jarvis_index_helpers.py (9 tests)
12	a9f5f9c	702	+9	kept	Add test_security_scan_helpers.py (9 tests)
13	b775a83	709	+7	kept	Add test_slack_poller_parse.py (7 tests)
14	70577ca	719	+10	kept	Add test_dream_helpers.py (10 tests)
15	48fc6ae	728	+9	kept	Add test_research_producer_helpers.py (9 tests)
16	091a766	739	+11	kept	Add test_jarvis_dispatcher_context_files.py (11 tests)
17	97900b1	745	+6	kept	Add test_overnight_runner_parse_program.py (6 tests)
18	e42971a	756	+11	kept	Add test_jarvis_dispatcher_sanitize.py (11 tests)
19	680c889	769	+13	kept	Add test_collect_sources.py (13 tests)
20	4eb1dc5	775	+6	kept	Add test_worktree_lock.py (6 tests)

## Notable Findings

- Flaky test: test_file_recency_single_file was intermittently failing due to Windows NTFS timestamp precision. Fixed in prod code (not just test).
- Import hygiene gap: test_collectors_prd_recency.py used a bare module import that worked in full suite (via conftest.py sys.path) but failed in isolation.
- Coverage gap: 17 scripts under tools/scripts/ had zero test coverage. This run added coverage for pure/utility functions in all major untested scripts.
- Security gates covered: validate_context_files, _scan_task_metadata_injection, _sanitize_anti_pattern_message, _validate_profile_content, safety_check all now have explicit test coverage.
