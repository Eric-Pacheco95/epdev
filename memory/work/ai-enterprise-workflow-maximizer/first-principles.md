# First-Principles Analysis: AI Enterprise Workflow Maximizer

**Date:** 2026-04-03
**Analyst:** Jarvis (adversarial mode)
**Subject:** Deployable Jarvis framework for TD Bank BA/BSAs and junior devs

---

## 1. What is the fundamental problem being solved?

Not "AI productivity." That's a category, not a problem.

The specific pain a BA/BSA at TD actually faces is this: **they spend 40-60% of their time translating between systems and people — not thinking.** Requirements go from stakeholders into Confluence docs. Confluence docs get parsed into Jira stories. Stories get described in emails. Emails produce clarification threads. None of this creates value. All of it requires context-switching, formatting, re-summarizing things that already exist. The BA is a human information router.

The problem this tool could solve: **structured thinking scaffolding that converts ambiguous inputs (meeting notes, email chains, stakeholder conversations) into structured work artifacts (requirements, stories, acceptance criteria) without the BA having to manually re-encode everything.** Claude Code's skill system — specifically `/create-prd`, `/delegation`, `/workflow-engine` — maps directly to this. That is a real, specific pain.

What it does NOT solve: anything involving production data, customer information, model governance, AML monitoring, or any of the bank's core operational systems. Those are compliance perimeters that no laptop-deployed tool breaches without an IT review board, a vendor assessment, and a risk committee sign-off.

**The honest answer**: this product solves a documentation and structured-thinking problem for knowledge workers. That is a narrower claim than "AI workflow maximizer" and should be presented as such — or it will be killed by the first compliance officer who reads the pitch.

---

## 2. What must be true for this to work?

Six irreducible requirements — with honest assessments of each:

**R1: Claude Code must run on a TD laptop.**
TD issues managed Windows machines with software restriction policies, DLP agents, and restricted developer tool installs. Claude Code requires Node.js (or the binary) and terminal access. Neither is guaranteed. On most bank laptops, installing npm packages from the internet is blocked at the network layer. This is the first gate and a genuine unknown — it cannot be assumed away.

**R2: The tool must produce zero false-confidence outputs on compliance-adjacent tasks.**
BAs use requirements artifacts downstream: security reviews, UAT sign-offs, audit evidence. If Claude hallucinates a regulatory reference or generates requirements language that sounds authoritative but is wrong, the BA copies it forward without scrutiny. This is a SOX-relevant failure mode. The tool's scope must be strictly bounded to tasks where errors are caught before they matter — draft artifacts, not final artifacts.

**R3: No bank data (client PII, transaction data, internal system names, project code names) must be sent to Anthropic.**
The current proposal relies on Claude's API (or Claude Code's hosted inference). TD will not approve a tool that routes internal work product through an external AI provider without a Data Processing Agreement, security assessment, and explicit data residency guarantees. As of 2026, Anthropic's enterprise agreements exist, but they require procurement involvement — not a one-person grassroots deploy.

**R4: The target user must have enough trust in the outputs to change their behavior.**
BA/BSAs at banks are risk-averse by selection. They have been burned by tools that promised automation and delivered garbage. If the first three uses produce one embarrassing output, the tool is dead. This means the initial skill set must be chosen for high reliability on narrow tasks, not broad coverage.

**R5: The content pipeline must not ingest confidential work product.**
The proposal combines a workflow tool with a content-generation pipeline that synthesizes "validated Jarvis markdown files, git commits, and memories" into LinkedIn/newsletter content. On a bank machine, those inputs will contain confidential project information. Any pipeline that auto-drafts public content from internal work output is a data exfiltration risk under TD's policies, regardless of intent.

**R6: There must be a sanctioned internal deployment path.**
Grassroots "I'll just install it on my laptop" is how consultants get escorted out of buildings. This requires either an IT exemption, an innovation lab sandbox, or a formal pilot program. Without one of these, the entire deployment model is an employment policy violation.

---

## 3. The most dangerous wrong assumptions

**Wrong assumption 1: "Bank laptop" is a deployment target.**
The proposal treats enterprise deployment as a software packaging problem — extract the harness, strip personal data, give users a CLAUDE.md. It is not. Enterprise deployment at a regulated FI is a governance problem. Every tool that runs on a bank-issued machine is subject to software asset management, DLP policy, change management, and information security review. The `/extract-harness` skill produces a clean repo. It does not produce an IT risk assessment, a data classification decision, or a vendor security questionnaire response. The packaging is 10% of the work. The governance is 90%.

**Wrong assumption 2: "BA/BSAs and junior devs" are the same user.**
These are different people with different tools, different approval chains, and different definitions of "useful." A junior dev has terminal access and can probably install Claude Code. A BA almost certainly cannot. A BA's output is a Word doc or Confluence page. A dev's output is a PR. The skill set, the distribution method, and the value proposition are different for each. A product that tries to serve both at once will be positioned for neither.

**Wrong assumption 3: OSFI E-23 compliance demand creates demand for this product.**
OSFI E-23 is a model risk management framework targeting ML models used in credit scoring, fraud detection, and risk quantification. It requires model inventories, validation, and governance. A workflow tool for BAs does not help with E-23 compliance — it does not touch the model layer. Invoking E-23 as demand context for this product is a category error. E-23 creates demand for model governance consultants. This product, if it does anything, helps BAs write better requirements. These are unrelated problems.

**Wrong assumption 4: The content pipeline is a natural byproduct.**
The framing is: "as a byproduct of daily work, synthesize into newsletter/LinkedIn drafts." This assumes that (a) internal work artifacts are appropriate inputs for public content, (b) users want to publish content about their work, and (c) automating this step reduces friction rather than creating compliance risk. At a bank, internal project work is confidential by default. No automated pipeline should be inferring what is safe to publish. The content pipeline does not become safer by being automatic — it becomes more dangerous, because it removes the human judgment step that catches confidentiality violations.

---

## 4. The simplest version that still delivers real value

Strip everything that creates compliance exposure. What remains:

**A portable CLAUDE.md harness with 8-12 pre-vetted skills for structured thinking tasks.**

The skills that survive: `/create-prd`, `/first-principles`, `/find-logical-fallacies`, `/delegation`, `/review-code`, `/architecture-review`, `/red-team`, `/workflow-engine`.

No memory system. No learning signals. No overnight workers. No content pipeline. No TELOS.

Distribution: a GitHub repo with a README, a one-page setup guide, and a single CLAUDE.md that users clone and open in Claude Code on their personal machines (not bank machines) for personal skill development. This sidesteps the enterprise deployment problem entirely.

**Value delivered**: a BA or junior dev who uses this on their personal machine becomes measurably better at structured reasoning and documentation — skills that transfer directly to their job. They bring better artifacts to work, not a tool to work.

This is less exciting than an "Enterprise Workflow Maximizer" and it is the version that is actually deployable without an employment policy violation.

---

## 5. Where the enterprise AI tooling playbook fails here

**Conventional wisdom says: sell to the enterprise, not the individual.**
Wrong for this market right now. Enterprise AI procurement at a regulated FI takes 12-18 months. The OSFI E-23 deadline is May 2027 — fourteen months away. A grassroots tool that individual contributors adopt personally (on personal machines, with personal API keys) can create internal champions who then pull the tool through procurement. The path to enterprise adoption runs through personal adoption, not the other way around.

**Conventional wisdom says: compliance requirements are a moat for sophisticated vendors.**
Partially wrong. Compliance requirements are a moat for tools that touch regulated data. A structured-thinking harness that runs on markdown files and produces requirements documents is not meaningfully more regulated than Microsoft Word. The moat argument is being used to justify complexity (compliance readiness features, governance documentation) that the minimum viable product does not need.

**Conventional wisdom says: enterprise users need onboarding, training, and support.**
True, but the target user here (technically literate BA/BSA, junior dev) can follow a README. The `/jarvis-help` pattern — self-documenting skills with DISCOVERY sections — handles most of the onboarding problem without building a support infrastructure. The enterprise software playbook says build a training program. The right answer is build better documentation.

---

## 6. Content pipeline: feature or separate product?

**It is a separate product. The first-principles argument:**

The workflow harness solves a structured thinking problem. Its users are knowledge workers who want better artifacts. Its value is measured by output quality: did this requirement get approved, did this design hold up, did this story get implemented without rework.

The content pipeline solves a thought leadership problem. Its users are professionals who want an audience. Its value is measured by engagement: did this post get impressions, did this newsletter get subscribers.

These are different users, different value propositions, different feedback loops, and critically — different risk profiles. Combining them means the compliance constraints of the content pipeline (don't ingest confidential work product) become constraints on the entire product. The content pipeline is the most legally exposed component of the proposal. Bundling it with the harness makes the harness harder to approve, not easier.

**Separate them.** Ship the harness first as a pure structured-thinking tool. The content pipeline, if it is built at all, should be positioned as a personal productivity tool for consultants and independent professionals — not for bank employees using it on work-adjacent inputs.

The one scenario where combining makes sense: if the entire product is pitched to non-bank users (solopreneurs, consultants, small business owners) where confidentiality constraints are lower. In that market, a "think better + publish what you learned" loop is coherent. For the stated target user — TD Bank BA/BSAs — it is a liability.

---

## Summary: What to Challenge Before Building

| Assumption | Verdict | Action Required |
|---|---|---|
| Bank laptop is a viable deployment target | False for v1 | Redesign for personal machines first |
| BA/BSAs and junior devs are one user | False | Pick one; BA is higher-value, harder to reach |
| OSFI E-23 creates demand for this product | False | Remove from pitch; it's a category error |
| Content pipeline is a natural byproduct | Dangerous | Separate it or cut it |
| Enterprise deployment is a packaging problem | False | It's a governance problem — out of scope for v1 |
| Users need broad skill coverage | False | 8 high-reliability skills beat 40 mediocre ones |
