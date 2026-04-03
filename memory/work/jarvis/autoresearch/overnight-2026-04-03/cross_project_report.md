# Cross-Project Coherence Report

- **Date**: 2026-04-03
- **Dimension**: cross_project
- **Branch**: jarvis/overnight-2026-04-03
- **Repos analyzed**: epdev, crypto-bot, jarvis-app

## Executive Summary

Cross-project coherence is generally strong: CLAUDE.md files share the ALGORITHM execution model, ISC methodology, and steering rules correctly. However, 7 inconsistencies were identified across naming, stale references, assumption drift, and missing governance.

## Findings

### F1: ISC Word Count Rule Divergence (MEDIUM)

- **epdev CLAUDE.md**: "Each criterion: concise, state-based, binary-testable" (no word count constraint)
- **crypto-bot CLAUDE.md**: "Each criterion: exactly 8 words, state-based, binary-testable"
- **Impact**: The "exactly 8 words" rule in crypto-bot is stricter than epdev's standard. This was likely an experimental constraint that was never reconciled. ISC criteria in epdev PRDs don't follow an 8-word rule.
- **Recommendation**: Align to epdev's "concise" standard. The 8-word constraint is artificial and can force awkward phrasing that hurts clarity.

### F2: Legacy "brain-map" Naming Persists in jarvis-app (LOW)

- **jarvis-app `package-lock.json`**: Still says `"name": "jarvis-brain-map"` (lines 2, 8)
- **jarvis-app `BrainMap.tsx:182`**: UI header says "JARVIS BRAIN MAP"
- **jarvis-app `config.ts:5`**: Legacy fallback `brain-map.config.json` still listed
- **jarvis-app `types.ts:127`**: Deprecated type alias `BrainMapConfig` still exported
- **epdev `orchestration/tasklist.md:524`**: References `memory/work/jarvis_brain_map/PRD.md` (old path; new PRD is at `memory/work/jarvis-app/PRD.md`)
- **epdev `.gitignore`**: Has entries for both `memory/work/brain_map/` and `memory/work/jarvis_brain_map/` (stale)
- **Impact**: Confusing for any session working on the app. The rename from FR-001 was partially completed.
- **Recommendation**: Run `npm pkg set name="jarvis-app"` + `npm install` in jarvis-app to update package-lock.json. The component name `BrainMap` is fine internally (it IS a brain map), but the UI header and deprecated type should be cleaned up. Fix the stale tasklist reference.

### F3: epdev Path Reference in crypto-bot is Stale (MEDIUM)

- **crypto-bot CLAUDE.md line 3**: References `C:\Users\ericp\Github\epdev`
- **crypto-bot CLAUDE.md line 47**: References `C:\Users\ericp\Github\epdev\orchestration\tasklist.md`
- **Actual path**: `C:\Users\ericp\Github\epdev` still exists alongside the `epdev-overnight` worktree, but the canonical repo moved off OneDrive. The path is technically correct but fragile -- any future move would break these references.
- **Impact**: Low risk currently since the path is valid, but the cross-repo coupling to an absolute Windows path is a maintenance burden.
- **Recommendation**: No immediate action needed. If epdev ever moves again, these references must be updated. Consider a future pattern where cross-repo paths are configured rather than hardcoded.

### F4: crypto-bot AGENTS.md References Cursor Cloud Agents (STALE)

- **crypto-bot AGENTS.md**: Entire document is written for "Cursor Cloud Agents" with Cursor-specific workflow (branch prefix `cursor/`, Cursor Secrets, etc.)
- **Memory**: "Eric has Claude Max; all implementation in Claude Code, Cursor retired"
- **Impact**: AGENTS.md is completely stale. Any session that reads it will get confused by Cursor-specific instructions. The agent roles (QA, ML, Scout, PM, QA Tester) are still valid concepts but the execution context is wrong.
- **Recommendation**: Either (a) rewrite AGENTS.md for Claude Code context using the Six-Section agent anatomy from epdev steering rules, or (b) archive it and rely on the roles defined in crypto-bot CLAUDE.md's Skill Registry section.

### F5: Telegram vs Slack Notification Channel Divergence (MEDIUM)

- **crypto-bot CLAUDE.md**: References Telegram for trade notifications and approval workflow (`alerts/telegram_bot.py`)
- **epdev tasklist**: Has parked items for "Slack Bot Socket Mode" and "Block Kit trade approval cards" that would replace Telegram
- **epdev CLAUDE.md**: Extensive Slack channel routing rules (#jarvis-inbox, #epdev, etc.)
- **Impact**: crypto-bot is on Telegram while epdev is on Slack. The planned migration to Slack for crypto-bot approvals hasn't happened. This means trade approval workflows are on a different platform than all other Jarvis notifications.
- **Recommendation**: This is a known parked item, not an inconsistency per se. But the crypto-bot CLAUDE.md should acknowledge that Slack migration is planned (or explicitly confirm Telegram is staying). Currently there's no mention of Slack at all in crypto-bot CLAUDE.md.

### F6: jarvis-app Has No CLAUDE.md (GOVERNANCE GAP)

- **jarvis-app**: No CLAUDE.md exists. No `.claude/` directory. No steering rules.
- **epdev CLAUDE.md steering rule**: "When onboarding a pre-existing project under Jarvis governance: (1) /deep-audit --onboard..."
- **Impact**: Sessions working in the jarvis-app repo get no Jarvis context -- no ALGORITHM loop, no ISC rules, no security constraints, no skill routing. The project is tracked in epdev's tasklist and has a PRD in epdev, but the repo itself is ungoverned.
- **Recommendation**: Create a minimal CLAUDE.md for jarvis-app that: (a) declares it as a Jarvis-managed project, (b) points to epdev for orchestration, (c) establishes the ALGORITHM loop, (d) defines the parser/config as the core architecture. This mirrors what crypto-bot CLAUDE.md does.

### F7: Signal Pipeline Max Points Mismatch (LOW)

- **crypto-bot CLAUDE.md line 121**: "P1 (LunarCrush): galaxy_score + alt_rank + sentiment + social_dominance (max 80, cap 35)"
- **crypto-bot AGENTS.md line 162**: "P1 | LunarCrush | 100"
- **crypto-bot plan.md**: "P1=LunarCrush (max 80)"
- **Impact**: AGENTS.md disagrees with CLAUDE.md and the plan on P1 max points (100 vs 80). This is another symptom of AGENTS.md being stale.
- **Recommendation**: Covered by F4 fix. AGENTS.md should be archived or reconciled.

## Coherence Matrix

| Dimension | epdev <-> crypto-bot | epdev <-> jarvis-app | crypto-bot <-> jarvis-app |
|-----------|---------------------|---------------------|--------------------------|
| ALGORITHM loop | Aligned | N/A (no CLAUDE.md) | N/A |
| ISC rules | **Diverged** (F1) | N/A | N/A |
| Naming | Clean | **Stale refs** (F2) | N/A |
| Cross-repo paths | **Fragile** (F3) | Clean (config.json) | N/A |
| Agent definitions | **Stale** (F4) | N/A | N/A |
| Notification channel | **Split** (F5) | N/A | N/A |
| Governance | Aligned | **Missing** (F6) | N/A |
| Signal architecture | **Mismatch** (F7) | N/A | N/A |

## Recommended Priority

1. **F6** (jarvis-app CLAUDE.md) -- governance gap, any session there is ungoverned
2. **F4** (crypto-bot AGENTS.md) -- stale Cursor references actively misleading
3. **F1** (ISC 8-word rule) -- diverged standard, easy one-line fix
4. **F2** (brain-map naming) -- cosmetic but frequent source of confusion
5. **F7** (pipeline max points) -- covered by F4
6. **F5** (Telegram vs Slack) -- known parked item, just needs acknowledgment
7. **F3** (epdev path) -- technically correct today, monitor only

## Run Log

iteration	commit_hash	metric_value	delta	status	description
0	baseline	0	0	baseline	Metric baseline established
1	report	0	0	kept	Cross-project coherence report written with 7 findings
