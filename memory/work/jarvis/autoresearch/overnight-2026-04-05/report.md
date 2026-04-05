# Cross-Project Coherence Report

> Generated: 2026-04-05 04:00 EDT
> Dimension: cross_project
> Projects analyzed: epdev, crypto-bot, jarvis-app

## Summary

Reviewed CLAUDE.md, skill registries, agent definitions, and structural conventions across all three Jarvis-governed repos. Found **7 inconsistencies** across 4 categories: naming, stale references, pattern divergence, and missing governance artifacts.

## Findings

### 1. STALE: crypto-bot AGENTS.md references deprecated Cursor workflow

**Severity: Low (cosmetic)**
**File**: `crypto-bot/AGENTS.md`
**Detail**: The entire file is marked DEPRECATED at line 3 ("This document was written for Cursor Cloud Agents. Eric now uses Claude Code.") but still exists as a 100+ line document. It references Cursor Secrets, `cursor/` branch prefixes, and agent roles (PM, Scout, Quant, ML) that are not wired into the current Claude Code skill system. The agent roles have conceptual value but the execution instructions are stale.
**Recommendation**: Either delete AGENTS.md or extract the conceptually valid role definitions into epdev-style agent definitions under `crypto-bot/.claude/agents/` or `epdev/orchestration/agents/`. The Cursor-specific instructions should be removed regardless.

### 2. DIVERGENCE: Agent definition format not shared to child repos

**Severity: Medium (governance gap)**
**Detail**: epdev has 5 Six-Section agent definitions in `orchestration/agents/` (Architect, Engineer, Orchestrator, QATester, SecurityAnalyst). crypto-bot has a Python `agents/` directory with `patch_proposer.py` and `strategy_analyst.py` -- these are runtime code, not agent definitions in the epdev format. jarvis-app has no agent definitions at all.
**Recommendation**: If agent definitions are meant to govern Claude Code behavior in child repos, they should either (a) live centrally in epdev and be referenced via CLAUDE.md context routing, or (b) be replicated in child repos using the Six-Section format. Current state is inconsistent -- epdev validates agent format with `validate_agents.py` but child repos don't participate.

### 3. INCONSISTENCY: ISC Quality Gate not enforced in child repos

**Severity: Medium (process gap)**
**Detail**: epdev's CLAUDE.md defines a 6-check ISC Quality Gate (Count, Conciseness, State-not-action, Binary-testable, Anti-criteria, Verify method) that blocks PLAN->BUILD. crypto-bot's CLAUDE.md references ISC format but does not include the Quality Gate checks. jarvis-app's CLAUDE.md doesn't mention the Quality Gate at all -- it defers to the PRD for ISC criteria.
**Recommendation**: The ISC Quality Gate is a Jarvis-wide standard. Add a brief reference in each child repo's CLAUDE.md pointing to epdev's canonical definition, e.g.: "ISC Quality Gate: see epdev CLAUDE.md. All ISC sets in this repo must pass the 6-check gate before BUILD."

### 4. STALE: crypto-bot references Telegram as transitional but no migration timeline

**Severity: Low (documentation drift)**
**File**: `crypto-bot/CLAUDE.md` line 111
**Detail**: Architecture section notes "Telegram is current but transitional" and references Slack migration in the epdev tasklist. However, the epdev tasklist has the Slack Bot Socket Mode item parked under "No demand signal within 60 days." These two signals contradict: crypto-bot implies migration is planned, epdev implies it's deprioritized.
**Recommendation**: Update crypto-bot's CLAUDE.md comment to reflect current state: "Telegram is current. Slack migration parked pending demand signal." This prevents a future session from starting migration work that isn't actually prioritized.

### 5. DIVERGENCE: Skill definition format inconsistency

**Severity: Low (cosmetic but confusing)**
**Detail**: epdev skills use `# IDENTITY and PURPOSE` as the opening section. crypto-bot skills also use `# IDENTITY and PURPOSE`. This is consistent. However, epdev's CLAUDE.md steering rule says "New agent definitions must use Six-Section anatomy" and references `validate_agents.py` -- but there is no equivalent validation for skill format consistency across repos. Skills in both repos follow the same pattern by convention only.
**Recommendation**: No action needed now, but if skill count grows in crypto-bot, consider adding the skill to epdev's validation tooling.

### 6. MISSING: jarvis-app has no .claude/settings.json or security validators

**Severity: Low (acceptable for read-only app)**
**Detail**: epdev has `security/validators/` with PreToolUse validation scripts and `.claude/settings.json` with hooks and permissions. crypto-bot has neither `.claude/settings.json` nor security validators. jarvis-app has neither. For jarvis-app this is acceptable (read-only dashboard, no secrets, no mutations). For crypto-bot (which handles wallet keys and API credentials), the absence of PreToolUse validators is a gap -- though crypto-bot's CLAUDE.md steering rules partially compensate.
**Recommendation**: Consider adding a minimal `.claude/settings.json` to crypto-bot with at least the absolute-path hook requirement and a PreToolUse validator for `.env` / wallet file protection.

### 7. INCONSISTENCY: Naming convention for repo references

**Severity: Low (cosmetic)**
**Detail**: epdev's CLAUDE.md and memory files refer to the app repo as both "brain-map" (memory index: `project_brainmap_kanban_phase.md`), "jarvis-brain-map", and "jarvis-app". The app's own CLAUDE.md settled on "jarvis-app" and explicitly documents the rename from `brain-map.config.json`. The epdev memory index still uses the old name.
**Recommendation**: Update the memory file name and description from `project_brainmap_kanban_phase.md` to reference "jarvis-app" consistently. The internal component name `BrainMap` is fine per jarvis-app's own CLAUDE.md.

## Coherence Matrix

| Dimension | epdev | crypto-bot | jarvis-app |
|-----------|-------|------------|------------|
| CLAUDE.md exists | Yes | Yes | Yes |
| Algorithm loop documented | Yes (full) | Yes (full) | Yes (abbreviated) |
| ISC format documented | Yes + Quality Gate | Yes (no gate) | Defers to PRD |
| Agent definitions | 5 (Six-Section) | 2 (Python code, not Six-Section) | None |
| Skills (.claude/skills/) | 40+ | 6 | 0 |
| Security validators | Yes | No | No |
| .claude/settings.json | Yes | No | No |
| MCP config (.mcp.json) | Yes | No | No |
| Context routing table | Yes | Yes | Yes |
| Steering rules | 30+ categorized | 14 flat | 8 (2 categories) |
| TELOS alignment stated | Yes | Yes | Yes |

## Run Log (TSV)

```
iteration	commit_hash	metric_value	delta	status	description
0	-	0	-	baseline	Metric is static (echo 0); this run produces a coherence report, not a measurable code improvement
1	(see below)	0	0	kept	Cross-project coherence report written
```

## Next Steps (for Eric)

1. **Quick win**: Delete or refactor `crypto-bot/AGENTS.md` (Finding 1)
2. **Quick win**: Update Telegram migration comment in crypto-bot CLAUDE.md (Finding 4)
3. **Quick win**: Rename `project_brainmap_kanban_phase.md` memory file (Finding 7)
4. **Medium effort**: Add ISC Quality Gate reference to child repo CLAUDE.md files (Finding 3)
5. **Consider**: Minimal security config for crypto-bot (Finding 6)
