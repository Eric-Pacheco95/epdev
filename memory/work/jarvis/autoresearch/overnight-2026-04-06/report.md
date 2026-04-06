# Cross-Project Coherence Report

- **Date**: 2026-04-06
- **Dimension**: cross_project
- **Branch**: jarvis/overnight-2026-04-06
- **Repos analyzed**: epdev, crypto-bot, jarvis-app
- **Prior report**: 2026-04-03 (7 findings)

## Executive Summary

Cross-project coherence improved since the April 3 report: F1 (ISC 8-word rule) was fixed in crypto-bot, F5 (Telegram/Slack acknowledgment) was added to crypto-bot CLAUDE.md, and F6 (jarvis-app governance gap) was resolved with a full CLAUDE.md. However, 4 of the original 7 findings remain open, and 3 new inconsistencies were identified -- primarily stale status references that have drifted as projects progressed.

### Findings from April 3: Resolution Status

| Finding | Status | Evidence |
|---------|--------|----------|
| F1: ISC 8-word rule divergence | **FIXED** | crypto-bot CLAUDE.md now says "concise" matching epdev |
| F2: Legacy "brain-map" naming | **OPEN** | `package-lock.json` still says `jarvis-brain-map`; `config.ts` still has legacy fallback; epdev `.gitignore` still has stale `brain_map/` and `jarvis_brain_map/` entries |
| F3: epdev path fragility | **OPEN** (monitor) | Paths still hardcoded; technically correct |
| F4: crypto-bot AGENTS.md Cursor refs | **OPEN** | 5 Cursor references remain in AGENTS.md |
| F5: Telegram/Slack acknowledgment | **FIXED** | crypto-bot CLAUDE.md architecture section now notes "Slack migration planned (see epdev tasklist). Telegram is current but transitional." |
| F6: jarvis-app CLAUDE.md missing | **FIXED** | Full CLAUDE.md exists with ALGORITHM loop, steering rules, context routing, skill registry |
| F7: Signal pipeline max points | **OPEN** | Covered by F4 -- AGENTS.md still stale |

## New Findings

### F8: jarvis-app Sprint Status Drift (MEDIUM)

- **jarvis-app CLAUDE.md**: Says "Sprint 1+2 complete. Active work: FR-001 rename + Phase 4 completion."
- **epdev tasklist.md**: Says "Sprint 1+2+3 COMPLETE (app shell, vitals, drill-down, tab restructure)"
- **Impact**: jarvis-app's own CLAUDE.md is behind its actual progress. Sprint 3 was completed but CLAUDE.md wasn't updated. The "Active Sprint: Phase 4 Completion" section may also be stale if FR-001 rename was finished.
- **Recommendation**: Update jarvis-app CLAUDE.md Status to reflect Sprint 3 completion and current active work.

### F9: crypto-bot Production Target Date Drift (LOW)

- **crypto-bot CLAUDE.md**: "Phase: Paper trading (March 2026) -> Production (target: April 2026)"
- **epdev tasklist.md**: crypto-bot health is "yellow" with "Paper trading -> production gate" as next action
- **Impact**: We are now IN April 2026. The production target date is either imminent or has slipped. The CLAUDE.md should reflect current reality -- either the target has been deferred or a specific gate criteria exists.
- **Recommendation**: Update crypto-bot CLAUDE.md Phase line to reflect actual production gate status (e.g., "Paper trading active. Production gate: see `docs/PRE_PRODUCTION_STATUS.md` for blocker status").

### F10: crypto-bot Has No .claude/settings.json (GOVERNANCE GAP)

- **crypto-bot**: Has `.claude/skills/` (6 domain skills) but no `.claude/settings.json`
- **jarvis-app**: Has CLAUDE.md but no `.claude/` directory at all
- **epdev**: Full `.claude/settings.json` with hooks, validators, permissions
- **Impact**: Neither satellite repo has hook-based governance (security validators, session start hooks, learning capture). Sessions in these repos rely entirely on CLAUDE.md steering rules with no automated enforcement. For crypto-bot specifically, the "never commit .env" and "never switch RUN_MODE to production" rules are enforced only by model compliance, not by validators.
- **Recommendation**: For crypto-bot, create a minimal `.claude/settings.json` with at least: (1) deny list for `.env`, `data/wallets.json`; (2) a PreToolUse hook that blocks `RUN_MODE=production` writes. For jarvis-app, lower priority since it's read-only and has no secrets.

## Coherence Matrix (Updated)

| Dimension | epdev <-> crypto-bot | epdev <-> jarvis-app | crypto-bot <-> jarvis-app |
|-----------|---------------------|---------------------|--------------------------|
| ALGORITHM loop | Aligned | Aligned (fixed) | Aligned |
| ISC rules | **Aligned** (fixed) | Aligned | N/A |
| Naming | Clean | **Stale refs** (F2) | N/A |
| Cross-repo paths | Fragile (F3) | Clean (config.json) | N/A |
| Agent definitions | **Stale** (F4) | N/A | N/A |
| Notification channel | Acknowledged (F5) | N/A | N/A |
| Governance (CLAUDE.md) | Aligned | **Aligned** (fixed) | N/A |
| Governance (hooks) | **Gap** (F10) | **Gap** (F10) | N/A |
| Status freshness | **Drifted** (F9) | **Drifted** (F8) | N/A |
| Signal architecture | Stale in AGENTS.md (F7) | N/A | N/A |

## Progress Since Last Report

- 3 of 7 findings resolved (F1, F5, F6)
- 4 findings remain open (F2, F3, F4, F7)
- 3 new findings identified (F8, F9, F10)
- Net coherence: **improved** -- the governance gap (F6) was the highest-priority finding and is now fixed

## Recommended Priority (Updated)

1. **F4** (crypto-bot AGENTS.md) -- stale Cursor references, actively misleading. Archive or rewrite.
2. **F10** (satellite repo settings.json) -- no hook enforcement in crypto-bot; production safety relies on model compliance alone
3. **F8** (jarvis-app sprint status) -- easy update, keeps CLAUDE.md trustworthy
4. **F2** (brain-map naming) -- `npm install` in jarvis-app + clean epdev .gitignore
5. **F9** (crypto-bot production date) -- update Phase line to reflect reality
6. **F7** (pipeline max points) -- covered by F4
7. **F3** (epdev path fragility) -- monitor only

## Run Log

iteration	commit_hash	metric_value	delta	status	description
0	baseline	0	0	baseline	Metric baseline established
1	pending	0	0	kept	Cross-project coherence report with 10 findings (3 fixed, 4 open, 3 new)
