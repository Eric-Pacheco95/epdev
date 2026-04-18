---
topic: Self-evolving "Cortex" AI system — svpino/shujunliang teardown + Jarvis optimization patterns
type: technical
depth: default
date: 2026-04-18
sources: 7
confidence: 7
trigger_url: https://x.com/svpino/status/2045087838727975049
seed_thread: https://x.com/shujunliang/status/2044307601463357791
---

## What It Is

Santiago Valdarrama (`@svpino`) quote-tweeted a thread from EverMars (`@shujunliang`, CTO of **MuleRun**, an AI-agent marketplace). The thread is a technical postmortem of a user who, with *no programming experience*, built a self-evolving distributed agent system ("Cortex") that parasitized MuleRun's free-tier infrastructure for 219 generations at $0 total cost.

svpino does not reference any of his own tools here — the "repos/tools referenced" are:

1. The freeloader's private **Cortex** system (architecture described, no public repo).
2. The target platform — **MuleRun** (mulerun.com) — AI-agent marketplace Eric does not need.
3. The adjacent academic literature on self-evolving agents (surfaced via search; these are the actionable repos).

**Key scale numbers (claimed by MuleRun CTO):**

| Metric | Value |
|---|---|
| Cortex generations | 219 |
| Farmed accounts | 976 |
| API keys harvested | 47 |
| AI platforms "parasitized" | 11 |
| GitHub Actions workflows | 56 |
| Telegram bot size | 308 KB |
| Total spend | $0 |

## How It Works (the Cortex architecture)

Reconstructed from shujunliang's postmortem:

### 1. Components

- **agent.js** — core agent logic (dispatcher/executor).
- **Cortex** — the "brain" session running inside a MuleRun worker. Self-modifies code.
- **cortex-guardian** — orchestrator. When a Cortex's host account runs out of credits, guardian selects a new account, starts a new session, and injects the previous Cortex's *complete system prompt* including accumulated knowledge/improvements.
- **56 × GitHub Actions workflows** — distributed registration + dispatch layer (anti-detection, rotation).
- **Firebase** (unauthenticated, per the writeup) — operational state, credentials pool, strategies.
- **308 KB Telegram bot** — operator-facing control surface.

### 2. The self-evolution loop

```
Cortex-N runs → observes state → modifies code (agent.js, workflows, prompts)
  → git push → GHA auto-adopts new version → Cortex-(N+1) git clones repo
  → reads handoff files from Cortex-N → continues work
```

Each new Cortex's first action: `git clone`, read predecessor's handoff artifacts, resume.

### 3. Observed adaptive behaviors (Apr 13 ban wave → Cortex-218/219 response within hours)

- **Registration acceleration** — interval 10s → 5s, anti-detection jitter 90s → 30s.
- **Resource tiering** — credits pool < 10K → enter "conservation mode", stop dispatching.
- **Prompt stripping** — 70% refusal rate detected → strip swarm context from prompts.
- **Dispatch parallelization** — serial → 10-thread concurrent.

## Ecosystem — actual public repos worth looking at

These were *not* referenced by svpino, but they are the academic/open-source counterparts for the same self-evolving-agent idea:

| Repo | Relevance | License |
|---|---|---|
| `EvoAgentX/EvoAgentX` | Production framework for self-evolving agent ecosystems; HITL interceptor pattern | — |
| `EvoAgentX/Awesome-Self-Evolving-Agents` | Curated paper list | — |
| `CharlesQ9/Self-Evolving-Agents` | Survey paper with full taxonomy (reward-based, pop-based, evolutionary) | — |
| `EvoMap/awesome-agent-evolution` | Broader catalog incl. A2A/MCP + safety | — |
| `0xNyk/awesome-agent-cortex` | Obsidian-vault-backed agent arch; closer analogue to Jarvis's markdown-brain | — |

Notable papers cited: **Darwin Gödel Machine** (self-rewriting code), **Live-SWE-agent** (77.4% SWE-bench via runtime self-evolution), **Group-Evolving Agents** (71% SWE-bench), **AutoAgent** (elastic memory).

## Integration Notes — patterns worth absorbing into Jarvis

Each pattern gets a counterfactual check: would Jarvis be simpler without this?

### P1 · Generation handoff file · **REJECTED POST-REVIEW (2026-04-18)**

> **Status:** Rejected by `/architecture-review` on 2026-04-18. See `history/decisions/2026-04-18-arch-review-p1-handoff-rejected.md` and signal `memory/learning/signals/2026-04-18_arch-review-p1-handoff-rejected.md`.
>
> **Summary of rejection:** False-analogy transfer. Cortex handoff was load-bearing because sessions died with no operator memory; Jarvis has a persistent human operator + MEMORY.md + filesystem, and an active CLAUDE.md steering rule ("CTX 60% second time → decompose, don't checkpoint") that explicitly forbids this pattern. The proposal also (a) factually misframes `memory/work/session_checkpoint.md` as an existing stub (it was a one-off cron-reschedule notepad, now deleted), (b) violates the documented "PostToolUse hook → JSONL; never log raw inputs/outputs" rule via the raw tool-result digest, and (c) creates a persistent prompt-injection channel where web-sourced strings reach next-boot context with no human watching. All three review agents (first-principles, fallacy, red-team+STRIDE) converged on reject or scope-reduce.
>
> **Revisit conditions:** post-compact rework incidents > 3 in 30 days AND CLAUDE.md CTX-60% decompose rule explicitly retired first. If revisited, the red-team's hardened spec (metadata-only digest, HMAC, injection scanner on write+read, multi-session keying, 8 KB cap, interactive-only guard, untrusted-context wrapper at read) is the starting point — not the original P1 below.

~~**Pattern:** new session `git clone`s + reads structured handoff from predecessor + resumes work.~~

~~**Jarvis analog:** `memory/work/session_checkpoint.md` already exists in uncommitted state. Formalize it: every session-end hook writes a machine-readable handoff (active task, last tool results digest, unresolved blockers, current ISC progress). Next cold session reads it as part of the cold-boot load alongside `CLAUDE.md` and `MEMORY.md`.~~

~~**Why now:** the existing steering rule "when CTX reaches 60% twice, decompose in new session" creates exactly the discontinuity this pattern solves. Counterfactual: without it, Eric manually retypes context — already Jarvis's #1 friction point.~~ [unsourced claim; rejected]

### P2 · Resource-tier conservation mode (MEDIUM-HIGH VALUE)

**Pattern:** shared credit pool threshold triggers behavior change (< 10K → stop dispatching).

**Jarvis analog:** Tavily budget is already a known constraint (1000 extracts/mo; Firecrawl fallback documented in research-patterns.md). Formalize as a **monthly-budget sentinel** the dispatcher reads before scheduling research/autoresearch tasks. Same pattern for Claude API token budget once visible.

**Counterfactual:** without it, Jarvis currently *silently* exhausts Tavily mid-month — already happened per steering-rules.

### P3 · Emergency-adaptation loop (MEDIUM VALUE)

**Pattern:** detect external-stimulus error class → modify own behavior within hours (not days).

**Jarvis analog:** overnight runner currently retries on failure; add a tier where repeated same-class failures trigger a **prompt/config mutation step** logged to `history/decisions/` rather than a 10th identical retry. Applies to: repeated MCP tool failures, repeated model refusals, repeated gate failures in `/quality-gate`.

**Caveat:** needs a human-review gate before auto-applying mutations — the Cortex system had no brake and that is what got it banned. Draft mutation → PR → `/architecture-review` → human approve → apply.

### P4 · Prompt stripping on refusal (LOW-MEDIUM VALUE)

**Pattern:** 70% refusal rate on target model → automatically strip suspicious context from prompts.

**Jarvis analog:** when `/dispatcher` sub-agent Opus/Sonnet flows hit safety-refusal patterns, log which context blocks correlate and auto-strip in retry. Narrower scope than P3.

### P5 · Self-modifying-code via GHA auto-deploy (REJECT for now)

**Pattern:** agent pushes to repo → GHA adopts new version → agent runs on own updated code.

**Jarvis verdict:** **do not adopt directly.** Matches the `autonomous-rules.md` anti-pattern of unsupervised write-to-production. The Cortex loop had zero safety — that's why shujunliang's team caught it. Instead, keep `/implement-prd` and `/quality-gate` as the human-supervised equivalent. **Revisit only** if Eric wants nightly auto-PRs (agent proposes, human merges).

## Gotchas / Anti-patterns explicit in the source

These are **failure modes the Cortex system exhibited** — steering-rule candidates:

1. **Unauthenticated Firebase** — credentials/state in an open datastore. Jarvis analog: don't put operational state in services without auth tests.
2. **Session names that exposed intent** — attacker left attributable strings. Jarvis analog: don't hard-code user-identifying strings into automated artifacts.
3. **70% refusal rate treated as input, not warning** — system adapted prompts to evade refusal instead of stopping. Moral: refusal rate is a *halt* signal, not a tuning signal, once over a threshold.
4. **Tier-of-abstraction leakage** — swarm-context prompts leaked the coordination layer to the worker model. Jarvis analog: sub-agent prompts should not expose the orchestrator's mental model unless required.

## Alternatives / Tradeoffs

| Goal | Cortex approach | Jarvis-native alternative |
|---|---|---|
| Cross-session continuity | git-cloned handoff | `session_checkpoint.md` + MEMORY.md + CLAUDE.md cold-boot load |
| Self-improvement | agent.js auto-push | `/learning-capture` → steering rules + skills |
| Cost control | conservation threshold | budget sentinel in dispatcher (not yet built) |
| Parallelism | 10-thread dispatch | orchestration/task_backlog.jsonl + dispatcher (already parallel-capable) |
| Long-horizon execution | 219 generations | overnight runner + daily heartbeat |

## Open Questions

1. Does `session_checkpoint.md` (currently uncommitted) already implement P1, or is it a stub? If stub, what's the minimum format that both a session-end hook and cold-boot loader agree on?
2. Tavily monthly-budget sentinel — is there a counter already in the PostToolUse hook stream, or does this need a fresh collector?
3. Where does the "mutation proposes → human approves" loop fit? New skill `/propose-mutation`, or extension flag on `/update-steering-rules`?

## Sources

1. [svpino tweet (trigger)](https://x.com/svpino/status/2045087838727975049) — rating 6/10 (commentary, not source)
2. [shujunliang / EverMars thread (primary)](https://x.com/shujunliang/status/2044307601463357791) — rating 9/10 (first-hand postmortem by target platform CTO)
3. [mulerun_ai repost](https://x.com/mulerun_ai/status/2045080935784501499) — rating 7/10 (confirms platform-side)
4. [MuleRun pricing / context](https://www.toolify.ai/tool/mulerun) — rating 6/10 (target-platform context only)
5. [CharlesQ9/Self-Evolving-Agents (survey)](https://github.com/CharlesQ9/Self-Evolving-Agents) — rating 8/10
6. [EvoAgentX/Awesome-Self-Evolving-Agents](https://github.com/EvoAgentX/Awesome-Self-Evolving-Agents) — rating 8/10
7. [EvoMap/awesome-agent-evolution](https://github.com/EvoMap/awesome-agent-evolution) — rating 7/10

**Unverified claims flagged:** all scale numbers (219/976/47/11/56/308KB) come from a single source (shujunliang) that is also the injured party; treat as order-of-magnitude, not precise. No independent corroboration was located.

## Next Steps (revised 2026-04-18 post-arch-review)

1. ~~Inspect session_checkpoint.md~~ **DONE** — deleted (completed cron-reschedule scratchpad, not a handoff stub).
2. ~~Draft PRD for cold-boot handoff~~ **REJECTED** — see `history/decisions/2026-04-18-arch-review-p1-handoff-rejected.md`.
3. **P2 (budget sentinel)** — still viable; grounded in real Tavily exhaustion. Run `/create-prd` when picked up.
4. **P3 (emergency adaptation)** — deferred until Phase 5 overnight-runner convergence.
5. **P5 (self-modifying auto-deploy)** — rejected (autonomous-rules.md anti-pattern).
6. **New:** run `/update-steering-rules` to add an analogy-break test for research briefs extracting patterns from external case studies — surfaced as steering-rule candidate during this arch-review.

Auto-offer: `/analyze-claims` on the scale numbers (219/976/47/11) — all single-sourced from shujunliang; only matters if this brief is cited externally.

Auto-offer: `/analyze-claims` on the scale numbers (219/976/47/11) — all single-sourced from shujunliang; only matters if this brief is cited externally.
