---
name: update-steering-rules
description: Analyze failures, synthesis, and feedback to propose new or updated CLAUDE.md steering rules
---

# IDENTITY and PURPOSE

Steering rules engine. Analyze failures, synthesis docs, and session feedback to propose new/updated AI Steering Rules in CLAUDE.md. Repeated failures = missing rules; validated approaches = rules to formalize.

# DISCOVERY

## Stage
LEARN

## Syntax
/update-steering-rules
/update-steering-rules --audit

## Parameters
- --audit: Audit mode -- health check + prune stale rules, merge related rules, move category errors, archive completed-phase references. Runs bi-weekly during interactive sessions or when rule count exceeds 45 / file exceeds 20KB

## Examples
- /update-steering-rules -- analyze recent failures and propose new rules
- /update-steering-rules --audit -- prune and consolidate existing rules

## Chains
- Before: /self-heal (failures feed rule proposals), /synthesize-signals (synthesis themes feed rules), /learning-capture (feedback signals)
- After: /security-audit (if security rule proposed, validate against constitutional-rules.md)
- Related: /review-code (for code-level patterns that become rules)
- Full: /synthesize-signals > /update-steering-rules > /security-audit (if security rule)

## Output Contract
- Input: Optional --audit flag
- Output: Numbered list of proposed rules with evidence, insertion point in CLAUDE.md, and rationale
- Side effects: Rules added to CLAUDE.md (after approval), update logged to history/decisions/

## autonomous_safe
false

# STEPS

## Step 0: INPUT VALIDATION

- If a flag is provided and it is not `--audit`: print "Usage: /update-steering-rules [--audit]" and STOP
- If `--audit` flag present: proceed to Mode: --audit
- If no flag: proceed to Mode: Default

## Mode: Default (no flag) — Propose new rules from evidence

- Read the current AI Steering Rules section from `CLAUDE.md`
- Read recent failure records from `memory/learning/failures/`
- Read recent synthesis documents from `memory/learning/synthesis/`
- Read feedback memories from the Claude memory system if available
- Identify patterns that warrant new rules:
  - Repeated failures with the same root cause → prevention rule
  - User corrections that apply broadly → behavioral rule
  - Validated approaches that should be default → preference rule
  - Security incidents → security rule (route to constitutional-rules.md if severe)
- For each proposed rule, apply the **routing decision tree** to select the target file:

### Routing Decision Tree (7 destinations — apply top-down, first match wins)

1. **`security/constitutional-rules.md`** — irreversible/high-blast-radius actions (credentials, injection defense, git push protection)
2. **`orchestration/steering/autonomous-rules.md`** — autonomous `claude -p` worker behavior only (producers, dispatcher, worktree, overnight runner); must NOT apply to interactive sessions
3. **`orchestration/steering/platform-specific.md`** — Windows/PS/hooks/MCP-specific; applies in both interactive and autonomous but NOT on non-Windows
4. **`orchestration/steering/research-patterns.md`** — external info consumption (web research, absorb, adopt-vs-absorb)
5. **`orchestration/steering/cross-project.md`** — cross-repo operations (crypto-bot, jarvis-app, non-epdev)
6. **`orchestration/steering/trade-development.md`** — financial research, trade signals, alpha development
7. **`CLAUDE.md`** — universal (interactive + autonomous, all platforms, all projects) and no domain above matches

**Accumulation rule:** If a proposed rule belongs to a domain with no existing sub-steering file AND a second rule for the same domain emerges in the same or adjacent session, propose a new sub-steering file (see "Proposing new sub-steering files" below) rather than adding both to CLAUDE.md.

- For each proposed rule:
  - State the rule clearly in one sentence
  - Cite the evidence (failure filename, synthesis theme, user feedback)
  - Explain why it matters (what goes wrong without it)
  - Apply the routing decision tree — name the target file and the destination number that matched
  - Check it doesn't conflict with existing rules in the target file
- **Pre-encode duplicate check (MANDATORY):** grep the target file AND every Context Routing doc for overlapping scope, same evidence signals, or identical how-to-apply bullets. Match found → UPDATE existing rule (reinforce evidence, tighten language); never append a duplicate — each inflates every cold session. Ref: 2026-04-19 R4 was already encoded as R1 in `incident-triage.md`; caught only by ad-hoc scan.
- Present all proposed rules for review before writing
- After approval, add rules to the appropriate file (not always CLAUDE.md — follow the routing)
- Log the update to `history/decisions/` with rationale

### Proposing new sub-steering files

Trigger: a domain has accumulated 2+ rules with no existing sub-steering file.

Template (`orchestration/steering/trade-development.md` as reference):
```markdown
# [Domain Name] — Steering Rules

> Behavioral constraints for [domain context]. Loaded by [which skills/configs inject it].
> Extracted from CLAUDE.md to reduce base context pressure.

## [Section Name]

- [rule 1]
- [rule 2]

## Loaded by

- [list skills or configs that inject this file]
```

Present to Eric before creating. After approval, add `DOMAIN_CONTEXT_ROUTING` entry in `tools/scripts/jarvis_dispatcher.py`.

## Mode: --audit — Health check + prune + consolidate

**Step A0: Calibration rollup (pre-audit)**
Run `python tools/scripts/calibration_rollup.py`; read `data/calibration_weekly.md`. RED metrics surface as additional health-check findings (non-blocking; triggers recommendation, not STOP).

**Step A: Health Check (deterministic)**

1. **Size check (CLAUDE.md)**: `wc -c CLAUDE.md` — report bytes and pass/fail against 20KB (20480 bytes)
2. **Rule count (CLAUDE.md)**: `grep -c '^- ' CLAUDE.md` — report count and pass/fail against 45-rule ceiling
3. **Sub-steering file health (NEW)**: For every file in the Context Routing table, run `wc -c <file>` and `grep -c '^- ' <file>`. Apply the same thresholds: ≤ 20,480 B per file, ≤ 8 rules per H2/H3 section (soft cap). Surface RED entries in the health table. Sub-files exceeding size cap are spinoff candidates (split by section into a more specific sub-file) — propose under Step B as MOVE/SPLIT.
4. **MODEL-DEP review**: `grep 'MODEL-DEP' CLAUDE.md` — list model-limitation rules; verify each is still current
5. **Conflict scan**: contradicting rules; universal-scoped rules that apply only to autonomous/specific contexts; compound rules violating ISC no-compound principle
6. **Cross-file consistency**: Read ALL sub-steering files in Context Routing table. Check for: rules duplicated between CLAUDE.md and sub-files; misrouted rules. Files: `security/constitutional-rules.md`, `orchestration/steering/autonomous-rules.md`, `platform-specific.md`, `research-patterns.md`, `cross-project.md`, `trade-development.md`, `isc-governance.md`, `ceremony-tier.md`, `incident-triage.md`, `model-effort-routing.md`, `producer-artifacts.md`, `frontend-ui.md`, `testing-governance.md`
7. **Staleness scan**: completed phases, one-time incident workarounds, magic numbers belonging in config
8. **Spinoff trigger (NEW)**: For each file checked above (CLAUDE.md and every sub-file), if any single H2/H3 section contains ≥10 rules AND the rules cluster into ≥2 distinct themes (≥3 rules each, identifiable by leading bold phrase or shared keyword), propose a new sub-steering file. Heuristic for cluster detection: group rules by first-noun-phrase or shared bold lead-in; if 2+ groups have ≥3 rules each, flag as spinoff candidate. Propose under Step B as a new SUB-FILE creation with rule list to migrate and a Context Routing entry for CLAUDE.md.
9. **Skill description hygiene (NEW)**: For every `.claude/skills/*/SKILL.md`:
   - **Missing/stub**: confirm `description:` frontmatter is present and non-empty. The string `IDENTITY and PURPOSE` as a description value (the legacy fallback rendered when frontmatter is absent) counts as missing — flag for transcription via `python tools/scripts/skill_frontmatter_transcribe.py --dry-run`.
   - **Sanitization**: re-run the description through `INJECTION_PATTERNS` and the 200-char length cap defined in `tools/scripts/skill_frontmatter_transcribe.py`. Any match is a hard flag — descriptions land in the cold-session system-reminder and bypass PreToolUse/PostToolUse hooks, so the data-layer is the only sanitization point.
   - **Drift**: for each SKILL.md modified in the last 30 days (`git log --since=30.days --name-only -- '.claude/skills/*/SKILL.md'`), check whether the same commit touched the `description:` frontmatter line (`git log -L '/^description:/,+1:<path>' --since=30.days`). Body-changed-without-description = STALE; flag for rewrite. Source: 2026-04-28 /architecture-review on skill-list pollution — red-team severity-Low maintenance-drift finding made into a recurring audit item.

Present health check results as a table before proceeding.

**Step B: Propose changes**
For each issue found, propose one of:
- **REMOVE**: Rule is stale, duplicated, or now handled by model defaults
- **MERGE**: Two or more related rules should be consolidated into one crisper rule
- **MOVE**: Rule belongs in a domain-specific file (autonomous-rules.md, a SKILL.md, constitutional-rules.md)
- **SPLIT**: Compound rule should be separated into distinct concerns
- **UPDATE**: Rule text is outdated but the concern is still valid — rewrite
- **SPINOFF**: Section in CLAUDE.md or oversized sub-file should become a new sub-steering file (triggered by Step A check 3 or 8). Follow "Proposing new sub-steering files" template; include the rules to migrate and the Context Routing entry to add
- **TRANSCRIBE**: SKILL.md is missing `description:` frontmatter (triggered by Step A check 9 missing/stub). Run `python tools/scripts/skill_frontmatter_transcribe.py --dry-run` then `--apply` Sanitization-flagged or drift-flagged descriptions are REWRITE, not TRANSCRIBE — manual authoring with security review.

Present all proposals in a numbered list with evidence. Wait for Eric's approval before making any changes.

**Step C: Execute approved changes**
Apply only approved changes. After edits, re-run the size and rule count checks to confirm both thresholds are met. Log the audit to `history/decisions/`.

# OUTPUT INSTRUCTIONS

- Only output Markdown
- Proposed rules: numbered list with evidence; show insertion point in CLAUDE.md
- Rules must be specific, actionable, and testable
- After writing: "Added N steering rules to CLAUDE.md from M evidence sources"
- If no new rules warranted: say so
- Never remove existing rules without explicit approval


# VERIFY

- Proposed changes shown to Eric before any CLAUDE.md modification | Verify: numbered list + evidence in output before changes
- --audit mode: size + rule count checked after edits | Verify: post-edit counts in output
- Audit logged to `history/decisions/` | Verify: `ls -t history/decisions/ | head -3`
- No rules removed without explicit approval | Verify: deletion confirmations in output
- New rules specific, actionable, testable | Verify: Read each added rule

# LEARN

- Track steering rule count — consistently > 45 → run --audit automatically before additions
- Same rule type added repeatedly → systemic gap; fix in tooling rather than adding more rules
- After --audit: note merged/removed categories — reveals worst-maintenance rule types
- [MODEL-DEP] rules → re-evaluate after major model upgrades

# INPUT

Analyze recent failures, synthesis, and feedback to propose steering rule updates.

INPUT:
