# Overnight Autoresearch Report — 2026-04-28
**Dimension:** prompt_quality  
**Branch:** jarvis/overnight-2026-04-28  
**Goal:** Reduce token count in verbose skills while preserving output quality

## Summary

- **Baseline:** 61,750 words across all SKILL.md files
- **Final:** 61,457 words
- **Total reduction:** -293 words (-0.47%)
- **Iterations:** 15 kept, 0 discarded
- **Guard:** none configured

## Approach

Targeted one focused change per skill per iteration. Priority order:
1. Corrupted/stale content (steps with broken template interpolation, hardcoded dates)
2. Stale references (skills that no longer exist, history notes)
3. Redundant content (intro sentences duplicating DISCOVERY, merged bullets)
4. Verbose formatting (numbered lists to compact inline, field semantics covered by JSON)
5. Over-long SKILL CHAIN parentheticals

Avoided touching: DISCOVERY structured headers, VERIFY | Verify: lines, autonomous_safe flags, fenced code blocks used as external agent templates.

## TSV Run Log

iter	commit	metric	delta	status	description
1	5341d50	61719	-31	KEPT	fix(vitals): remove corrupted stale steps 6.5/6.6 with hardcoded failure paths
2	25b8a2f	61713	-6	KEPT	fix(jarvis-help): remove stale /label-and-rate skill reference
3	f9473bc	61664	-49	KEPT	refactor(make-prediction): compress DOMAIN LENS DETAILS to dense format
4	7424e1f	61656	-8	KEPT	refactor(vitals): remove stale morning_feed.py history annotation
5	e86b081	61635	-21	KEPT	refactor(second-opinion): merge LEARN bullets into single compact line
6	92b98ba	61620	-15	KEPT	refactor(create-prd): compress RISKS section instruction in OUTPUT INSTRUCTIONS
7	fafe2a5	61601	-19	KEPT	refactor(skills): remove stale Replaces/verbose Composes from SKILL CHAINs
8	47505fe	61592	-9	KEPT	refactor(architecture-review): compress Step 2.5 CANARY agent prompt
9	8e0cbf6	61566	-26	KEPT	refactor(implement-prd): compress catch-rate log field semantics
10	63e982c	61558	-8	KEPT	refactor(research): remove stale Phase 6A.1 tracking label from vector-wins
11	7508e71	61527	-31	KEPT	refactor(extract-harness): compress ENTERPRISE gap-analysis list + push-status note
12	eba94e4	61507	-20	KEPT	refactor(notion-sync): remove redundant MODES intro (covered by DISCOVERY Parameters)
13	c2dbafa	61494	-13	KEPT	refactor(make-prediction): compress BACKCAST questions and security rule
14	5400a48	61476	-18	KEPT	refactor(skills): compress sequencing rule and sub-steering approval note
15	8acbf9b	61457	-19	KEPT	refactor(skills): compress implement-prd SKILL CHAIN + fix stale date in notion-sync

## Notable Quality Fixes (Beyond Word Count)

| Finding | Severity | File |
|---------|----------|------|
| Steps 6.5/6.6 broken template vars + hardcoded April-2026 failure paths | HIGH | vitals/SKILL.md |
| /label-and-rate listed as skill but directory does not exist | MEDIUM | jarvis-help/SKILL.md |
| VERIFY grep used hardcoded date 2026-04-27 -- broken for any other date | MEDIUM | notion-sync/SKILL.md |
| Phase 6A.1 Signal 2 tracking label -- stale internal reference | LOW | research/SKILL.md |
| morning_feed.py history annotation -- stale replaced-skill note | LOW | vitals/SKILL.md |

---

# Cross-Project Coherence Report — 2026-04-28

> Overnight dimension: `cross_project`
> Repos analyzed: epdev, crypto-bot, jarvis-app

## Executive Summary

3 repos share a common governance framework (TheAlgorithm, ISC, Jarvis orchestration) with good structural alignment but 7 actionable inconsistencies: 2 stale references, 2 naming drift issues, 2 missing cross-project contracts, and 1 assumption mismatch.

## Findings

### F1: STALE — crypto-bot production timeline (sev: medium)

**Location:** `crypto-bot/CLAUDE.md:11`
**Issue:** States `Production (target: April 2026)` — it is now 2026-04-28, paper trading is offline due to Moralis 2M CU overage (epdev tasklist line 10), and reactivation is blocked until ~2026-05-03. The target date is stale.
**Impact:** New sessions in crypto-bot will see an expired target date, creating confusion about project status.
**Fix:** Update to reflect current reality: `Production (target: TBD — paper trading paused, Moralis cap reset ~2026-05-03)`.

### F2: STALE — jarvis-app Active Sprint section (sev: medium)

**Location:** `jarvis-app/CLAUDE.md:11, 78-83`
**Issue:** Status says `Sprint 1+2 complete. Active work: FR-001 rename + Phase 4 completion` and the Active Sprint section describes Phase 4 work. Per epdev tasklist, Sprints 1-4 are COMPLETE and Sprint 5 (design system) is also COMPLETE as of 2026-04-25.
**Impact:** Sessions in jarvis-app start with outdated sprint context, potentially re-doing completed work.
**Fix:** Update Status to `Sprints 1-5 complete` and Active Sprint to reflect current state.

### F3: NAMING DRIFT — legacy brain-map artifacts in jarvis-app (sev: low)

**Location:** `jarvis-app/src/lib/config.ts:5-8`, `jarvis-app/src/lib/graph/types.ts:127`
**Issue:** Config loader still falls back to `brain-map.config.json` and exports `BrainMapConfig` as a type alias. CLAUDE.md says the config was renamed — but the fallback and alias remain as dead backward-compat code.
**Impact:** Low — functional but signals incomplete rename migration.
**Recommendation:** Remove `brain-map.config.json` from `CONFIG_FILES` array and delete the `BrainMapConfig` type alias.

### F4: NAMING DRIFT — epdev path references (sev: info)

**Location:** All three repos
**Issue:** Both satellite repos reference `C:\Users\ericp\Github\epdev` as the orchestrator path. This is correct. Non-issue.

### F5: MISSING CONTRACT — jarvis-app has no LEARN phase signal routing (sev: low)

**Location:** `jarvis-app/CLAUDE.md` — no mention of signal capture
**Issue:** crypto-bot routes LEARN signals to `epdev/memory/learning/signals/` with `Source: crypto-bot`. jarvis-app's CLAUDE.md mentions the 7-phase loop but never specifies signal routing.
**Impact:** Learning signals from jarvis-app sessions are lost or ad-hoc.
**Fix:** Add to jarvis-app steering rules: `After sessions with non-trivial learnings, write a signal to epdev memory/learning/signals/ with Source: jarvis-app`.

### F6: MISSING CONTRACT — crypto-bot default branch not self-documented (sev: low)

**Location:** `orchestration/steering/cross-project.md:10`, `crypto-bot/CLAUDE.md`
**Issue:** Cross-project steering doc warns crypto-bot uses `master` not `main`. But crypto-bot's own CLAUDE.md never states its default branch. Without loading cross-project.md, sessions would assume `main`.
**Fix:** Add `- **Default branch**: master` to crypto-bot Identity section.

### F7: ASSUMPTION MISMATCH — Telegram vs Slack migration status (sev: info)

**Location:** `crypto-bot/CLAUDE.md:111`, `epdev/orchestration/tasklist.md:115`
**Issue:** Both repos agree migration is planned and gated. Currently doubly-blocked (not production-stable + Moralis blocker). Tracked correctly. No action needed.

## Coherence Scorecard

| Dimension | Status | Notes |
|-----------|--------|-------|
| TheAlgorithm 7-phase loop | Aligned | All 3 repos use it |
| ISC methodology | Aligned | Consistent framework, per-repo specialization |
| Orchestration hub | Aligned | Both satellites point to epdev/orchestration/tasklist.md |
| Security policy | Aligned | jarvis-app defers to epdev; crypto-bot has local + epdev |
| Signal/LEARN routing | **Gap** | crypto-bot routes to epdev; jarvis-app unspecified (F5) |
| Naming consistency | **Drift** | brain-map artifacts linger in jarvis-app (F3) |
| Status freshness | **Stale** | crypto-bot production target (F1), jarvis-app sprint (F2) |
| Default branch docs | **Gap** | crypto-bot doesn't self-document `master` (F6) |
| Skill registries | Aligned | crypto-bot has domain skills + references epdev universals |
| Data contracts (vitals) | Aligned | Schema v1 defined in epdev, referenced by jarvis-app |

## TSV Run Log (cross_project dimension)

iteration	commit_hash	metric_value	delta	status	description
0	-	0	-	baseline	Static metric — coherence report dimension
1	(report)	0	0	kept	Cross-project coherence report written to disk

## Recommendations (Priority Order)

1. **F1** — Update crypto-bot production timeline (stale date creates confusion)
2. **F2** — Update jarvis-app active sprint section (4 sprints behind current state)
3. **F5** — Add LEARN signal routing to jarvis-app CLAUDE.md
4. **F6** — Add default branch to crypto-bot Identity section
5. **F3** — Clean up brain-map legacy artifacts in jarvis-app (low priority, code-level)
