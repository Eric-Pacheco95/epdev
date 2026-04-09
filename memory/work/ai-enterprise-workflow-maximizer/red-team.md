# Red-Team Analysis: AI Enterprise Workflow Maximizer
**Date:** 2026-04-03
**Analyst role:** Adversarial — find kills, not fixes
**Scope:** TD Bank BA/BSA and junior dev deployment of a portable Jarvis harness

---

## 1. Enterprise IT Gatekeeping

**Fantasy path:** IT reviews the tool, sees it's just a CLI wrapper on Claude, approves in 2 weeks.

**Reality path:** Claude Code is a developer tool that opens a persistent shell, executes arbitrary Bash commands, reads the full filesystem, and makes outbound HTTPS calls to `api.anthropic.com` on every message. That profile triggers three independent security review queues at any Big 5 bank: endpoint security (DLP agents will flag an AI tool that can read the filesystem), network security (outbound to a third-party AI API = data egress risk under PCI-DSS), and vendor risk management (Anthropic must pass a third-party vendor assessment — SOC 2 Type II, data residency declaration, model training data usage policy).

TD already has enterprise AI tooling under active governance. Adding a second, uncontrolled AI endpoint from a single practitioner's GitHub repo is a non-starter through normal channels. The realistic path requires: (a) Anthropic's enterprise agreement with data-residency guarantees, (b) a formal vendor assessment, (c) DLP policy exceptions for the AI API endpoint, (d) application whitelisting for Claude Code on managed endpoints. That process takes 6-18 months at a Big 5, not weeks. The tool will likely be blocked at the network layer long before any human reviews it.

---

## 2. Target User Mismatch

BA/BSAs at TD do not have admin rights on their laptops. Full stop. They run Windows on managed endpoints with application whitelisting, endpoint detection and response (EDR) agents, and a locked-down npm/Python environment.

Specific breakage points:
- `npm` and `npx` are blocked or absent — Claude Code's MCP server transport layer dies here
- Python may be available but only through a corporate-approved distribution (Anaconda Enterprise or similar) with restricted package installs
- `git` may be absent entirely — BA/BSAs are not developers; this is not a safe assumption
- Shell execution (`bash`, PowerShell unrestricted) is locked down by CyberArk or a PAM solution
- Installing Claude Code itself requires admin elevation on first run

Junior devs fare better — they likely have some developer tooling — but they still operate under IT-managed environments with package installation requiring a ticket. The install experience for this tool, even after IT approval, involves a multi-hour setup process that requires a developer-level IT support ticket for each user. At a bank, that creates a per-seat onboarding cost that kills grassroots adoption.

---

## 3. The Content Pipeline as a Liability

This is the highest legal-risk component. Auto-generating LinkedIn posts and newsletters by scanning git commits and memory files at a bank employee's work laptop creates several distinct liability vectors:

**MNPI contamination.** If any work commit touches a system involved in a material transaction — a merger integration, a trading desk tool, a regulatory filing — and that context leaks into auto-generated public content, that is a potential securities violation. The user does not need to knowingly include MNPI for it to appear. Synthesize-signals does not understand what is material.

**IP ownership.** Under standard employment agreements at every Big 5 bank, work product created using company resources (including a work laptop) belongs to the employer. Content generated from work git commits and work memories is arguable employer property. Publishing it externally without approval violates the employment agreement, regardless of how generic it appears.

**Confidentiality.** OSFI-regulated institutions have confidentiality obligations that extend to business processes, not just customer data. Synthesizing internal workflow patterns into public content — even without naming the bank — can breach confidentiality obligations.

**The pipeline hides the risk.** The danger is not a single deliberate disclosure. It's a user who forgets that last week's commit touched a sensitive project, runs synthesize-signals, and publishes. The auto-generation step removes the human checkpoint that would normally catch this.

---

## 4. Open Source Risk

If the repo ships with the constitutional security rules included, a fork that removes them creates a tool that an inexperienced deployer can point at a bank laptop with no guardrails. The liability exposure for the original author is real but limited — you cannot be held liable for downstream misuse of open-source software under most jurisdictions' interpretations of open-source license terms, provided the license is clear about "no warranty."

The more concrete risk is reputational and professional. If a competitor or a news outlet connects a security incident at a financial institution to a tool that originated from an employed TD Bank practitioner's GitHub, the employment consequences are severe even if the legal exposure is low. The fork is not traceable to you after the fact — but the originating repo is.

The second-order open source risk: publishing a working AI workflow harness for banks before getting employer approval is itself a violation of most Big 5 IP assignment clauses. The tool was likely built with ideas developed during employment, using knowledge of bank workflows. Open-sourcing first, asking permission later, is a termination-level event.

---

## 5. Adoption Failure Modes

**Failure mode 1: Setup friction kills momentum before first use.**
A BA receives a GitHub link, a README, and instructions to install Claude Code. They hit the first error — likely a missing dependency or a network block — and they stop. There is no IT support contract, no onboarding session, no one to call. The tool's value is invisible until after a successful first run. Most users quit before that run happens.

**Failure mode 2: The tool is too powerful, so IT bans it retroactively.**
A junior dev gets it working, starts using it productively, mentions it to their manager. Manager mentions it to IT. IT sees an AI tool with shell access and filesystem read that phones home to Anthropic. They ban it without appeal. All users on the same endpoint policy lose access simultaneously. There is no rollback or negotiation path because the tool was never formally approved.

**Failure mode 3: The skill system requires a mental model users don't have.**
The 40-skill harness is powerful for someone who built it. For a BA who has never used a CLI-driven workflow tool, the cognitive overhead of skill discovery, skill chaining, and ISC-based task structuring is high. They will use it as a chat box, miss 90% of the value, and conclude "it's just another AI assistant." The skill-first model requires users to think in workflows before they can benefit — that is a learned behavior, not an intuitive one.

---

## 6. The "/extract-harness POC Worked" Trap

The POC ran on your personal laptop: admin rights, no DLP, no EDR, no network filtering, npm/npx available, Python in PATH, git configured, Claude Code already authenticated. The sum of those conditions is the exact opposite of a managed bank endpoint.

Specific gaps that the POC does not surface:

- **Authentication.** Claude Code authenticates to Anthropic via browser OAuth. On a managed endpoint with a locked-down browser profile, this flow may be blocked by SSO intercept or outbound URL filtering.
- **File system paths.** The harness uses hardcoded paths (`memory/work/`, `history/decisions/`). On a managed endpoint, the user's home directory may be a network share with latency and locking behaviors that break shell operations.
- **EDR false positives.** CrowdStrike or SentinelOne will flag shell commands spawned by a Node.js process (Claude Code's architecture) as suspicious. This may trigger automatic process kill or a security incident ticket — not just a warning.
- **Skill scale.** The POC tests one or two skills. At 40 skills, the CLAUDE.md context load at session start is significant. On a constrained endpoint, session startup latency becomes a UX problem.
- **Git dependency.** Several skills assume `git` is configured with a user identity. BA laptops may have git absent or unconfigured.

The extraction process itself (`/extract-harness`) is well-designed. The gap is that extracting a clean artifact does not validate whether the artifact can run in the target environment. Those are separate problems.

---

## 7. Single Biggest Threat

**The content pipeline violates employment obligations before the product ships.**

Every other risk on this list is a deployment or adoption problem — things that kill the product after it launches. The content pipeline — specifically, auto-generating public professional content from work laptop git commits — violates the employment agreement before a single user installs the tool. If the employment agreement has a standard IP assignment clause (it does, at every Big 5 bank), content generated from work-context commits using work-acquired knowledge is arguable employer property. If it includes a confidentiality clause (it does), synthesizing internal workflow patterns into public LinkedIn content is a breach.

This is not a legal risk that manifests at scale. It manifests the first time Eric or any user runs the pipeline on a work commit and publishes. The risk is not theoretical — it is one `synthesize-signals` run away from a conversation with HR.

The MNPI angle makes it worse: if a single synthesized post is ever connected to a material non-public event, the consequences are not just employment-related. They are regulatory.

This component should be removed from the product entirely, not scoped out of the enterprise version. Its presence in the proposal poisons the entire framing.

---

## Risk Severity Table

| Risk | Likelihood | Impact | Severity | Killshot? |
|------|-----------|--------|----------|-----------|
| IT network/endpoint blocking | Very High | Product never deploys | Critical | Yes |
| Content pipeline — IP/MNPI violation | High | Termination + regulatory | Critical | Yes |
| Target users lack admin rights / tooling | Very High | Zero installs | Critical | Yes |
| Open source before employer approval | High | Termination | Critical | Yes |
| Setup friction kills BA adoption | Very High | Near-zero retention | High | No |
| EDR false positives on managed endpoints | High | Tool banned retroactively | High | No |
| Skill mental model mismatch for BAs | High | Underutilization | Medium | No |
| Vendor risk review timeline (6-18 mo) | Very High | Long delay | High | No |
| Open source fork removes guardrails | Medium | Reputational | Medium | No |
| Git dependency absent on BA laptops | High | Skill failures | Medium | No |

**Four killshots exist.** Any one of them ends the project. The content pipeline and the open source timing are the only two that could also end the employment relationship.
