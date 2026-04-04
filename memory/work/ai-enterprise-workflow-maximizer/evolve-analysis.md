# claude-workbench --evolve Gap Analysis
**Date:** 2026-04-04
**Tool:** claude-workbench (enterprise AI workflow harness for bank BA/BSAs and junior devs)
**Analysis type:** Structured gap analysis — workflow, knowledge, templates, compliance, strategic

---

## 1. Workflow Gaps

| Gap | Who | Effort | Priority | Notes |
|-----|-----|--------|----------|-------|
| Meeting notes → structured action items + decisions + owner table | BA/BSA | S | P1 | Daily use; absorb handles raw ingestion but no meeting-specific extraction schema |
| Email/Slack thread → requirements extraction | BA/BSA | S | P1 | Common pre-sprint task; absorb + create-prd is two hops; a single `/extract-requirements` is faster and teachable |
| Regulatory bulletin → impact analysis for active projects | BA/BSA | M | P1 | OSFI/FINTRAC updates drop irregularly; no skill maps bulletin language to current project NFRs |
| Change request → impact assessment (scope, risk, dependencies) | BA/BSA | M | P1 | CR workflow is universal; no structured template + skill pairing exists |
| Acceptance criteria → test case generation | BA/BSA + Dev | M | P2 | Manual test case writing is high-volume, low-creativity; strong LLM candidate |
| Sprint retro → lessons capture | BA/BSA + Dev | S | P2 | Template exists; no `/sprint-retro` skill to drive the conversation and commit output |
| Vendor / tool assessment (RFI response scoring) | BA/BSA | M | P2 | Structured scoring matrix with weighted criteria; recurs at procurement cycles |
| Data dictionary / schema documentation from DDL or API spec | Dev | M | P2 | Junior devs reverse-document existing systems; no skill for schema-in → doc-out |
| "Get me up to speed on project X" onboarding | Both | M | P3 | Ingest docs/absorbed/ + sprint-log + stakeholders → 1-page brief; useful for contractors |
| Existing system doc → gap analysis vs. new requirements | BA/BSA | L | P3 | Useful but complex; defer until core P1/P2 slots are filled |

---

## 2. Knowledge Gaps

| Gap | Effort | Priority |
|-----|--------|----------|
| PIPEDA summary (privacy law — NFR source for data handling, consent, breach notification) | S | P1 |
| Data classification framework (public / internal / confidential / restricted) with handling rules | S | P1 |
| OSFI B-10 (Third-Party Risk) summary — common in vendor assessments and API integrations | S | P1 |
| Open Banking Canada framework (FCAC roadmap, consent model, API standards) | M | P2 |
| Security review checklist — OWASP Top 10 mapped to banking context | M | P2 |
| Testing standards reference (unit / integration / UAT / regression definitions, coverage targets) | S | P2 |
| Common architecture patterns for banking (API gateway, event-driven, CQRS, saga) | M | P3 |
| FINTRAC AML/KYC obligations summary (triggers: onboarding, transactions, reporting) | S | P3 |

---

## 3. Template Gaps

| Template | Effort | Priority |
|----------|--------|----------|
| User story with structured AC (Given/When/Then + DoD checklist) | S | P1 |
| Change request (scope delta, risk rating, approvals, rollback plan) | S | P1 |
| Test plan (scope, approach, entry/exit criteria, environment, sign-off) | S | P1 |
| Vendor/tool assessment (weighted scoring matrix, risk flags, recommendation) | S | P2 |
| Data flow diagram description (prose template for Visio/Miro hand-off) | S | P2 |
| Release notes (audience-split: exec summary + technical delta + rollback) | S | P2 |
| Incident report / post-mortem (timeline, impact, root cause, action items) | M | P3 |
| Runbook / operational procedure (step-by-step, owner, escalation path) | M | P3 |

---

## 4. LLM Compliance Gaps

Current CLAUDE.md has no compliance section. The following additions are required before this tool is used with any real work product at a bank:

1. **Data prohibition rule** — Add explicit rule: "Never paste client data, PII, account numbers, internal system names, or MNPI into prompts. All examples must use synthetic data. If you are unsure whether content is confidential, do not paste it." This must be the first rule in the file, not buried.

2. **AI-assisted artifact labeling** — All outputs written to `docs/` must include a footer: `_AI-assisted draft — reviewed and approved by [name] on [date]. Not for external distribution without human review._` Add a steering rule enforcing this for `/create-prd`, `/write-essay`, and template fills.

3. **Commit message audit trail** — The `/commit` skill should append `[AI-assisted]` to commit messages when Claude authored substantive content in that session. This creates an auditable signal without being burdensome.

4. **Model usage logging** — Add a `data/usage-log.jsonl` file that appends one record per session: `{date, skills_used[], approximate_tokens_estimate, session_purpose}`. This supports compliance reporting if the bank ever asks "how are you using AI tools?"

5. **Employment agreement alignment** — Add a one-time setup prompt in `/project-init`: "Confirm you have reviewed your employer's AI/technology use policy. This tool runs on your personal machine with your personal API key, but outputs you bring to work may be subject to your employment agreement. When in doubt, treat outputs as your own work product and review before submitting."

6. **No IP laundering rule** — Add rule: "Do not use this tool to reproduce, paraphrase, or reconstruct proprietary bank documentation, vendor IP, or licensed content. Absorbing a competitor's architecture diagram to extract patterns is acceptable; reproducing it verbatim is not."

---

## 5. Strategic Assessment

| Dimension | Internal Play | External Play | Hybrid |
|-----------|--------------|---------------|--------|
| **Time to first value** | 3-6 months (find sponsors, build demo) | 12-18 months (MVP + first paying customer) | 6-9 months internally, then 18+ externally |
| **Employment risk** | Zero | High without employer approval | Low-to-medium (transparent internal use reduces risk) |
| **Upside** | Promotion / new role / internal funding | Uncapped if category takes off | Medium internal + option on external |
| **Validation source** | Real problems from real colleagues | Must sell to get signal | Internal = free validation loop |
| **IP ownership** | Bank likely owns work-product | You own it (personal machine, personal API) | Ambiguous if internal role is formal |
| **Execution dependency** | Org politics, champion needed | Revenue + distribution muscle needed | Sequencing discipline required |
| **Kill risk** | Absorbed into existing team with no credit | Market commoditized by incumbents (Copilot for Finance, etc.) | Stalls at internal stage, never converts |

**Recommended sequence — Hybrid:**

1. **Months 1-3:** Use claude-workbench personally. Build a portfolio of 5-10 before/after artifacts (requirements doc quality, time saved, regulatory analysis). This is your proof of concept with zero risk.
2. **Months 3-6:** Run an informal lunch-and-learn or Teams post. Find 2-3 BA/BSA colleagues who want to use it. Gather structured feedback. You are now an internal evangelist, not a product manager.
3. **Months 6-12:** Pitch an "AI workflow" working group to your manager. Frame as productivity improvement, not a product. Goal: get 15-20 internal users and a sponsor above your level. Optionally formalize as an innovation project.
4. **Months 12-18:** Decision gate — is TD moving fast enough for you? If yes, push for a formal AI tooling role. If no, review employment agreement, consult legal, and begin building the external version (different enough to be original, using your personal track record as GTM).

**What the internal pitch looks like:** "I've been using a personal AI harness to improve my requirements artifacts. I'd like to run a 30-day pilot with 5 volunteers to measure quality delta and time savings. I need 30 minutes of your time to scope it." Simple. Low risk. Measurable.

**External pricing anchor (if it gets there):** $49/user/month for the hosted harness + knowledge base. Target: boutique consultancies, community banks, credit unions — not Big 5 (sales cycle too long). Distribution: LinkedIn content + BA community of practice forums.

---

## 6. Recommended Backlog — Top 10

| # | Item | Type | Effort | Priority |
|---|------|------|--------|----------|
| 1 | `/extract-requirements` skill (email/Slack/meeting → structured requirements) | Skill | S | P1 |
| 2 | PIPEDA + data classification knowledge files | Knowledge | S | P1 |
| 3 | User story + change request templates | Template | S | P1 |
| 4 | LLM compliance section in CLAUDE.md (all 6 rules above) | Compliance | S | P1 |
| 5 | `/meeting-debrief` skill (notes → actions + decisions + owners) | Skill | S | P1 |
| 6 | `/regulatory-impact` skill (bulletin text → affected NFRs + projects) | Skill | M | P1 |
| 7 | `/sprint-retro` skill (drives structured retro conversation → lessons file) | Skill | S | P2 |
| 8 | Test plan + test case generation template + skill | Template + Skill | M | P2 |
| 9 | OSFI B-10 + Open Banking Canada knowledge files | Knowledge | S | P2 |
| 10 | Vendor assessment template + `/vendor-assess` skill | Template + Skill | M | P2 |

**Total estimated effort for P1 items:** ~3-4 focused sessions (P1 items are all S/M).
**Biggest ROI item:** `/extract-requirements` — eliminates the most manual daily work for the target user with the smallest build investment.
