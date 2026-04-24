# Overnight Run Report — prompt_quality — 2026-04-24

## Summary

| Field | Value |
|-------|-------|
| Dimension | prompt_quality |
| Branch | jarvis/overnight-2026-04-24 |
| Baseline | 62857 words |
| Final | 62025 words |
| Delta | -832 words (-1.3%) |
| Iterations | 15 |
| Kept | 15 |
| Discarded | 0 |

## Strategy

Targeted verbose prose in the 6 largest skill files. Each iteration compressed one logical section — explanatory text around schemas, duplicated inline criteria, wordy step descriptions — without changing the semantic content or removing functional instructions. No templates were truncated, no rule lists were dropped.

Files touched:
- implement-prd/SKILL.md (5 passes: catch-rate log, model annotation, subagent flow, escalation check, verifiability + hygiene + checkpoint)
- architecture-review/SKILL.md (2 passes: canary cross-read, evidence gathering)
- create-prd/SKILL.md (5 passes: ISC gate criteria, model annotation heuristic, blocker pre-check, paired-prd check, task typing rubric + socratic brainstorm)
- learning-capture/SKILL.md (1 pass: tier check + source engagement)
- make-prediction/SKILL.md (1 pass: domain-specific orient sections)
- second-opinion/SKILL.md (1 pass: ground rules in both templates)

## TSV Run Log

iter	commit	metric	delta	status	description
1	22470e0	62834	-23	KEEP	implement-prd: compress catch-rate log explanation
2	627582d	62802	-32	KEEP	implement-prd: compress model annotation check
3	b06a3d3	62707	-95	KEEP	architecture-review: compress canary cross-read section
4	3593a2b	62669	-38	KEEP	create-prd: compress inline ISC quality gate criteria
5	38e84fa	62587	-82	KEEP	create-prd: compress model annotation heuristic rules
6	0d033b3	62536	-51	KEEP	create-prd: compress blocker-list evidence pre-check
7	df8c59a	62516	-20	KEEP	implement-prd: compress review gate subagent flow
8	c8c5700	62438	-78	KEEP	learning-capture: compress tier check + source engagement
9	6375cdd	62392	-46	KEEP	make-prediction: compress domain-specific orient sections
10	b2fc6d0	62368	-24	KEEP	second-opinion: compress ground rules in both templates
11	45182f1	62351	-17	KEEP	implement-prd: compress escalation check
12	ca37f3c	62265	-86	KEEP	create-prd: compress paired-prd check
13	5848927	62153	-112	KEEP	architecture-review: compress evidence gathering step
14	7ee92e7	62093	-60	KEEP	implement-prd: compress verifiability routing + hygiene + checkpoint
15	3ec65ee	62025	-68	KEEP	create-prd: compress task typing rubric + socratic brainstorm

---

# Overnight Run Report — codebase_health — 2026-04-24

## Summary

| Field | Value |
|-------|-------|
| Dimension | codebase_health |
| Branch | jarvis/overnight-2026-04-24 |
| Baseline | 1893 pytest passing |
| Final | 2008 pytest passing |
| Delta | +115 tests (+6.1%) |
| Iterations | 20 |
| Kept | 20 |
| Discarded | 0 |

## Strategy

Added unit tests for pure helper functions across `tools/scripts/` and extended existing test suites rather than creating parallel ones. Each iteration targeted a different script or coverage gap, importing the function directly and exercising boundary conditions, error paths, and edge cases. No subprocess-dependent or I/O-heavy functions were targeted — only functions with deterministic, controllable inputs.

Files touched:
- `tests/test_stamp_prd_axes.py` (new — 20 tests, stamp_prd_axes.py pure classifiers)
- `tests/test_calibration_rollup.py` (new — 26 tests, calibration_rollup.py metric helpers)
- `tests/defensive/test_security_scan.py` (extended — +13 tests, apply_false_positive_filter)
- `tests/test_corpus_extractor.py` (new — 20 tests, corpus_extractor.py extraction helpers)
- `tests/test_research_producer.py` (new — 21 tests, research_producer.py topic helpers)
- `tests/test_jarvis_index.py` (new — 15 tests, jarvis_index.py parser helpers)
- `tests/test_dream.py` (new — 19 tests, dream.py synthesis theme helpers)
- `tests/test_overnight_runner.py` (new — 21 tests, next_dimension/dimensions_to_run/validate_command)
- `tests/test_isc_executor_helpers.py` (new — 17 tests, isc_executor.py helpers)
- `tests/test_jarvis_dispatcher.py` (new — 34 tests, dispatcher security and routing helpers)
- `tests/test_lib_pure_helpers.py` (new — 18 tests, lib/task_proposals.py + lib/worktree.py)
- `tests/test_self_diagnose.py` (new — 27 tests, self_diagnose_wrapper.py helpers)
- `tests/test_embedding_service_helpers.py` (new — 33 tests, _sanitize_text, _classify_query, _is_excluded)
- `tests/test_code_prescan.py` (extended — +17 tests, format_table branches + _sanitize_ascii)
- `tests/test_vitals_collector_helpers.py` (extended — +22 tests, AI pricing + tavily usage)
- `tests/test_isc_validator_checks.py` (extended — +13 tests, parse_frontmatter + _redact_secrets)
- `tests/test_jarvis_dispatcher.py` (extended — +15 tests, validate_context_files + metadata scan)
- `tests/test_overnight_runner.py` (extended — +15 tests, parse_program)
- `tools/scripts/overnight_path_guard.py` (fix — reverse-remap for worktree pre-remapped paths)

## TSV Run Log

iter	commit	metric	delta	status	description
1	055f7d2	1893	0	KEEP	fix(path-guard): reverse-remap main-repo paths in worktree context
2	24cd9b8	1913	+20	KEEP	test(stamp-prd-axes): add 20 tests for pure classifiers
3	c94f462	1939	+26	KEEP	test(calibration-rollup): add 26 tests for metric helpers
4	4135373	1952	+13	KEEP	test(security-scan): extend with apply_false_positive_filter cases
5	459d77b	1972	+20	KEEP	test(corpus-extractor): add 20 tests for extraction helpers
6	02f18a2	1993	+21	KEEP	test(research-producer): add 21 tests for topic helpers
7	d987964	2008	+15	KEEP	test(jarvis-index): add 15 tests for signal frontmatter and log name parsers
8	d2858d2	2027	+19	KEEP	test(dream): add 19 tests for synthesis theme helpers
9	257d293	2048	+21	KEEP	test(overnight-runner): add 21 tests for dimension routing
10	d85ce8c	2065	+17	KEEP	test(isc-executor): add 17 tests for scrub_secrets and exit codes
11	9a8d0e8	2099	+34	KEEP	test(jarvis-dispatcher): add 34 tests for security and routing helpers
12	7a4cfce	2117	+18	KEEP	test(lib-helpers): add 18 tests for validate_proposal and _exclude_file_has_line
13	5f7f86e	2144	+27	KEEP	test(self-diagnose): add 27 tests for diagnosis helpers
14	c341bff	1926	+33	KEEP	test(embedding-service): add 33 tests for pure helpers
15	454afa2	1943	+17	KEEP	test(code-prescan): extend with 17 branch-coverage tests
16	38fa98e	1958	+15	KEEP	test(vitals-collector): add 15 AI pricing tests
17	65111c6	1971	+13	KEEP	test(isc-validator): add 13 tests for parse_frontmatter and _redact_secrets
18	3d5bbeb	1978	+7	KEEP	test(vitals-collector): add 7 collect_tavily_usage tests
19	1520d21	1993	+15	KEEP	test(jarvis-dispatcher): add 15 context validation tests
20	c2f89fb	2008	+15	KEEP	test(overnight-runner): add 15 parse_program tests
