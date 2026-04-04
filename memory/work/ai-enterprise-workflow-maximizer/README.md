# AI Enterprise Workflow Maximizer — Project Index

**Status:** Research complete, backlog defined, ready for roadmap + build
**Repo:** claude-workbench (C:\Users\ericp\Github\claude-workbench)
**Date:** 2026-04-04

---

## Project Summary

Deployable Jarvis framework (skills library + active memory system + templates) for bank BA/BSAs and junior devs. Runs on personal machines with personal Claude API keys. Users bring better artifacts to work.

**Strategic direction:** Hybrid — internal validation first (months 1-12), external product decision at month 12 gate.

**Current state:** 28 skills, active memory (glossary, templates, regulatory context, decision logging, lessons-learned), OSFI E-23 reference. Committed + pushed to GitHub.

---

## Materials Index

| File | What it contains |
|------|-----------------|
| `market-research.md` | Competitive landscape: who's selling AI workflow tools to enterprises, pricing, "don't build" signals |
| `evolve-analysis.md` | Gap analysis: workflow gaps, knowledge gaps, template gaps, LLM compliance gaps, strategic assessment |
| `first-principles.md` | First-principles decomposition from /project-init Phase 2 |
| `red-team.md` | Red-team stress test from /project-init Phase 3 |

---

## Key Findings

### Market
- No commercial Claude Code harness exists (all OSS)
- Anthropic building governance layer natively — don't compete there
- Gap is domain-specific workflow intelligence (bank/FI skills)
- Window closes late 2026

### Strategy
- Hybrid: internal validation → external product at month 12 gate
- 15-20 internal users with measurable quality data = the credential
- Content pipeline (Substack "Building Jarvis") feeds both paths

### Architecture Review (from content pipeline analysis)
- "Passive income" framing killed — this is deferred-revenue active work
- Differentiation: AI systems for builders, demonstrated through real work (Jarvis build-in-public)
- Newsletter-first → hybrid at 1K subscribers

---

## P1 Backlog (next session)

| # | Item | Type | Effort |
|---|------|------|--------|
| 1 | `/extract-requirements` (email/Slack -> structured reqs) | Skill | S |
| 2 | `/meeting-debrief` (notes -> actions + decisions + owners) | Skill | S |
| 3 | `/regulatory-impact` (bulletin -> affected NFRs per project) | Skill | M |
| 4 | LLM compliance section in workbench CLAUDE.md (6 rules) | Compliance | S |
| 5 | PIPEDA + data classification knowledge files | Knowledge | S |
| 6 | User story + change request + test plan templates | Templates | S |

## P2 Backlog

| # | Item | Type | Effort |
|---|------|------|--------|
| 7 | `/sprint-retro` skill | Skill | S |
| 8 | Test case generation from AC | Skill | M |
| 9 | OSFI B-10 + Open Banking Canada knowledge | Knowledge | S |
| 10 | `/vendor-assess` skill + template | Skill + Template | M |

---

## Content Pipeline

**Location:** `tools/scripts/content_pipeline/`
**Status:** Built, safety filter tested (33 sources passing, 9 correctly skipped)
**Next:** Run pipeline from standalone CMD to generate first draft, then validate tone

---

## Next Steps (fresh session)

1. Roadmap the P1 backlog with ISC criteria
2. Build P1 items (3-4 sessions estimated)
3. Run content pipeline for first Substack draft
4. Add LLM compliance rules to workbench CLAUDE.md
5. Set up Task Scheduler for weekly content pipeline
