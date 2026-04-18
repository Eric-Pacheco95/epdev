# PRD: Research Brief Promotion Gate

**Slug**: research-brief-promotion
**Date**: 2026-04-18
**Status**: DRAFT

---

## OVERVIEW

The Research Brief Promotion Gate is an autonomous overnight pipeline that evaluates `/research` skill outputs (`research_brief.md`) for domain knowledge fitness using a 3-tier quality gate — structural fitness, internal consistency, and cross-source Tavily verification — then deposits passing briefs into `memory/knowledge/<domain>/` as `raw_article` type for ingestion by the weekly domain knowledge consolidator. The gate runs as a new component of the overnight runner, writes no files in the main working tree (worktree-safe), and is silent on failure (signal logged, brief stays in `memory/work/`). A one-time migration run on the 27 existing briefs serves dual purpose: populating the knowledge base and providing human-in-the-loop validation data on gate decision quality.

---

## PROBLEM AND GOALS

- `/research` skill produces high-quality external domain knowledge but has no integration path into `memory/knowledge/` — output is orphaned in `memory/work/` indefinitely
- 27 existing research briefs are unreachable by the domain knowledge consolidator
- Manual promotion is incompatible with the autonomous learning loop goal
- Autonomous scanning of all `memory/work/` was rejected (arch-review 2026-04-18): loop-closure risk, TELOS blast radius, keyword-matching failures for internal artifacts
- **Goal**: close the `/research` → `memory/knowledge/` gap with a quality gate sufficient to replace human review, without modifying the domain knowledge consolidator

---

## NON-GOALS

- Does not promote arch-review outputs (`_arch-review-*/`) — those route to `history/decisions/`
- Does not modify `domain_knowledge_consolidator.py`
- Does not add a force-promote override (no human bypass of gate)
- Does not run during interactive sessions — overnight runner only
- Does not process any `memory/work/` file except `*/research_brief.md`
- Does not retroactively re-evaluate already-promoted briefs

---

## USERS AND PERSONAS

- **Jarvis (autonomous)**: runs the gate nightly, promotes or silently rejects each brief
- **Eric (passive beneficiary)**: domain knowledge improves without action; reviews one-time migration summary to validate gate quality

---

## USER JOURNEYS OR SCENARIOS

**New brief (steady state)**
1. Eric runs `/research <topic>` → brief written to `memory/work/<topic>/research_brief.md` with `domain:` frontmatter
2. Overnight runner detects path not in `data/promotion_gate_state.json`
3. Gate runs Tier 1 → Tier 2 → Tier 3 sequentially; stops at first failure
4. PASS: brief copied to `memory/knowledge/<domain>/YYYY-MM-DD_<slug>.md`; state file updated; signal logged
5. FAIL: brief stays in `memory/work/`; state file updated with fail tier + reason; signal logged

**One-time migration (first run)**
1. Migration script runs gate on all 27 existing `research_brief.md` files
2. Outputs a summary table: brief | domain inferred | tier failed | promoted?
3. Eric reviews summary to validate gate decision quality (HITL checkpoint)
4. Passing briefs promoted; state file seeded so they aren't re-processed

**Missing `domain:` frontmatter**
1. Brief exists without `domain:` field (pre-frontmatter-standardization)
2. Tier 1 fails immediately: "domain not identifiable"
3. Signal logged; brief stays in `memory/work/` with note to re-run `/research` with updated SKILL.md

---

## FUNCTIONAL REQUIREMENTS

**FR-001** Gate script `tools/scripts/promote_research_brief.py` accepts a file path and returns one of three outcomes: `promoted`, `failed:<tier>:<reason>`, `skipped:already-processed`

**FR-002** Tier 1 — Structural fitness (LLM-free heuristics + `domain:` frontmatter check):
- `domain:` frontmatter field present and maps to a known domain in `_DOMAIN_KEYWORDS`
- File age ≤ 180 days (stale content fails)
- File size > 200 chars (non-empty brief)
- Dir name does not match personal-research blocklist: `byd_canada_ev`, `aron-prins-research`, `smart-home-business`, `evolution-big-bang`, `telos` (and any dir under `memory/work/telos/`)

**FR-003** Tier 2 — Internal consistency (Sonnet LLM pass, no web access):
- Extract all factual/empirical claims from the brief
- Rate each: `strong`, `moderate`, `weak`, `unsupported` against the brief's own cited sources
- Fail condition: 3 or more claims rated `weak` or `unsupported`

**FR-004** Tier 3 — Cross-source verification (Tavily):
- Extract top 5 empirical claims from the brief
- Issue max 2 Tavily searches per claim (10 total cap)
- Score each claim: `corroborated`, `contradicted`, `unverifiable`
- Fail condition: >40% of verifiable claims contradicted, OR >60% of all claims unverifiable
- Tavily results sanitized before LLM injection: length-capped at 500 chars/result, injection patterns stripped per `INJECTION_SUBSTRINGS`

**FR-005** On PASS: copy brief to `memory/knowledge/<domain>/YYYY-MM-DD_<slug>.md` via git worktree (same worktree pattern as consolidator); add standardized frontmatter: `source_type: research_brief`, `promoted: YYYY-MM-DD`, `domain: <domain>`, `gate_tier_scores: {t1: pass, t2: pass, t3: <score>}`

**FR-006** On FAIL: do not touch `memory/knowledge/`; write signal to `memory/learning/signals/YYYY-MM-DD_promo-fail-<slug>.md` with tier, reason, and brief path

**FR-007** State file `data/promotion_gate_state.json` tracks every processed brief by absolute path with outcome and timestamp; gate is idempotent — running twice on same file returns `skipped:already-processed`

**FR-008** Overnight runner integration: poll `memory/work/*/research_brief.md`, cross-reference state file, run gate on new entries; max 5 briefs per overnight run (rate limit to control Tavily spend)

**FR-009** `/research` SKILL.md updated to include `domain:` frontmatter field in `research_brief.md` output template, populated from the research topic domain at write time

**FR-010** One-time migration script `tools/scripts/migrate_research_briefs.py`: runs gate on all 27 existing briefs, outputs markdown summary table for Eric review; does not auto-commit — Eric confirms before promotion is finalized

**FR-011** Tier 2 and Tier 3 use separate Sonnet subagents — generator (brief) and evaluator (claims analysis) are never the same model instance, per autonomous-rules model routing constraint

---

## NON-FUNCTIONAL REQUIREMENTS

- Gate completes in < 3 minutes per brief (Tier 1 < 5s, Tier 2 < 45s, Tier 3 < 120s)
- Max 10 Tavily calls per brief (Tier 3 cap)
- Gate script is read-only on `research_brief.md` source files
- All `memory/knowledge/` writes happen in a git worktree, never in main working tree
- Tier 3 Tavily results sanitized before LLM injection (OWASP LLM01 guard)

---

## ACCEPTANCE CRITERIA

- [ ] Every `memory/work/*/research_brief.md` not in `data/promotion_gate_state.json` is evaluated within the next overnight run after file creation | Verify: After overnight run, check state file contains entry for all `memory/work/*/research_brief.md` paths older than the run start time [E][M] | model: haiku |

- [ ] A brief passing all 3 tiers appears as `memory/knowledge/<domain>/YYYY-MM-DD_<slug>.md` in the git worktree commit of the same overnight run | Verify: `git log --name-only` on the knowledge worktree branch shows the promoted file in the overnight run commit [E][M] | model: haiku |

- [ ] A brief failing any tier does NOT appear in any `memory/knowledge/` subdirectory | Verify: For a known-fail brief, `grep -r <slug> memory/knowledge/` returns no matches after overnight run [E][A] | model: haiku |

- [ ] A signal file is written to `memory/learning/signals/` for every gate decision (pass and fail) containing tier result and reason | Verify: `ls memory/learning/signals/ | grep promo` shows one file per processed brief after migration run [E][M] | model: haiku |

- [ ] Tier 3 issues no more than 10 Tavily search calls per brief | Verify: Gate script logs show ≤ 10 Tavily calls in the run output for any single brief [I][M] | model: haiku |

- [ ] A brief with missing or unknown `domain:` frontmatter fails Tier 1 and is NOT promoted | Verify: Run gate on a brief with `domain: unknown`; confirm state file records `failed:tier1` and no file appears in `memory/knowledge/` [E][A]

- [ ] The state file prevents re-running the gate on an already-processed brief — second invocation returns `skipped:already-processed` without any Tavily calls or LLM calls | Verify: Run gate twice on same brief; check Tavily call count = 0 on second run and state file has single entry for that path [E][A]

**ISC Quality Gate: PASS (6/6)**

---

## SUCCESS METRICS

- 27 existing briefs evaluated; ≥ 15 promoted (estimate based on content quality observed)
- Migration summary reviewed by Eric within 1 week of ship
- Gate false-positive rate (Eric manually identifies a promoted brief that shouldn't be) < 10% over 90 days
- Gate false-negative rate not tracked (silent fail by design — Eric can re-research if a topic is thin)

---

## OUT OF SCOPE

- Arch-review outputs (`_arch-review-*/`)
- PRD files, TELOS files, session checkpoints in `memory/work/`
- Any modification to `domain_knowledge_consolidator.py`
- Force-promote / human override bypass
- Promotion of `/teach` outputs (separate evaluation needed)

---

## DEPENDENCIES AND INTEGRATIONS

- `data/promotion_gate_state.json` — new state file (created on first run)
- `tools/scripts/promote_research_brief.py` — new gate script
- `tools/scripts/migrate_research_briefs.py` — one-time migration script
- Overnight runner — new polling step added
- `/research` SKILL.md — `domain:` frontmatter field added to output template
- Tavily MCP (`mcp__tavily__tavily_search`) — Tier 3 cross-verification
- Claude Sonnet — Tier 2 and Tier 3 LLM calls
- Worktree pattern — same as `domain_knowledge_consolidator.py` (`epdev-knowledge-worktree`)
- `INJECTION_SUBSTRINGS` in `security/validators/validate_tool_use.py` — Tier 3 sanitization

---

## RISKS AND ASSUMPTIONS

### Risks

- **Tavily rate limits**: 10 calls/brief × 5 briefs/night = 50 calls max per run; within typical Tavily plan limits but should be monitored
- **Tier 3 unverifiable rate**: highly technical or niche claims (e.g., specific framework benchmarks) may be unverifiable via web search, triggering false failures — threshold set at 60% unverifiable, but some domains (crypto DeFi mechanics, cutting-edge AI benchmarks) may need domain-specific calibration
- **`domain:` backfill gap**: existing 27 briefs lack standardized `domain:` field — migration script must infer domain via keyword matching for these (exactly the fallback we want to avoid going forward); mark inferred domains as `domain_confidence: inferred` in promoted frontmatter
- **Worktree conflict**: if consolidator and promotion gate run in the same overnight window on the same worktree, conflict possible — gate should use a separate named worktree (`epdev-research-promo-worktree`)

### Assumptions

- `/research` skill is the only unintegrated external knowledge producer (validated by skill audit 2026-04-18)
- 3-tier gate replaces human review with Eric's explicit approval (acknowledged deviation from autonomous-rules staging requirement; gate is the compensating control)
- Overnight runner can be extended with a new polling step without architectural changes
- Tavily search results for factual claims are sufficient for cross-verification (may need recalibration for rapidly-changing domains)

---

## OPEN QUESTIONS

- ~~Should the migration summary be delivered via Slack (`#epdev`) or written to a file Eric reads manually?~~ **Resolved**: Slack `#epdev`
- ~~Should `domain_confidence: inferred` briefs from migration be promoted automatically or held for Eric to confirm separately?~~ **Resolved**: Hold as `manual_review` in migration summary; auto-promote decision deferred until migration results reveal gate quality
- ~~What is the overnight runner's current polling interval — does a 3-min gate script per brief fit within the window for 5 briefs (15 min total)?~~ **Resolved**: Fits within current window
