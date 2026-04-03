# Fallacy Detection — Knowledge Wiki Proposal

**Analyst role**: Adversarial logical analyst  
**Date**: 2026-04-03  
**Proposal**: Add Karpathy-style LLM-compiled domain knowledge layer to Jarvis  
**Verdict summary**: Motivated reasoning on top of a sound structural gap. Core need is real; the proposed scope is 3x too large and the analogy is materially broken.

---

## 1. FALSE ANALOGIES

### 1a. Karpathy is building a knowledge base FOR a team / public audience. Eric is building one for himself alone.

Karpathy's pattern solves a **recall and discoverability problem at scale** — large corpora, many sources, multi-reader wikis, backlinks needed to navigate a large knowledge graph. The LLM-compiled wiki makes sense when the corpus is too large for one person to hold in their head, or when output needs to be readable by others.

Eric's context: one user, domains that are relatively narrow (crypto trading, AI infra, security), and a working memory system already in place. The "wiki" overhead — backlinks, cross-links, concept articles, index maintenance — is **navigation infrastructure that solves a scale problem Eric doesn't have yet**.

**Where the analogy holds**: The core insight — raw sources should be ingested before they decay, and outputs should be filed, not discarded — applies. That's the salvageable piece.

**Where it breaks**: Karpathy almost certainly has hundreds of sources per domain per month. Eric's actual research output rate is unknown, but the existing signals system (~284 signals over an inferred multi-month period) suggests a modest input rate, not a corpus-scale problem.

### 1b. Karpathy's raw/ is static web clips. Eric's domain knowledge is embedded in live artifacts.

Eric already has:
- Trade logs in crypto-bot
- Research outputs from /research (ephemeral, but recoverable)
- Signals and synthesis that capture learned conclusions
- Steering rules that encode hard-won domain knowledge

Karpathy's raw/ layer solves the problem of external content that would otherwise be lost. Eric's knowledge gap is more likely **not losing his own outputs** — a different problem with a simpler solution (filing, not wiki compilation).

### 1c. "LLM linting for inconsistencies" assumes a wiki large enough to have inconsistencies worth finding.

At 10–50 articles, inconsistency detection is trivial and can be done by eye. Linting pays off at 500+ articles where human review is impractical. Building linting infrastructure now is pure speculative cost.

---

## 2. SCOPE CREEP SIGNALS

### 2a. The proposal adds 3 new system components when the stated need is "domain knowledge doesn't persist."

The minimal fix for "research outputs are ephemeral" is: **file the output**. That's one additional step in /research. Instead, the proposal introduces:
- A new `memory/knowledge/` directory tree with per-domain raw/ + wiki/ + index.md
- Two new skills (/research-ingest, /knowledge-query)
- An overnight linting job
- A new frontend view in jarvis-app (brain-map knowledge browser)

The frontend view alone is a separate multi-day build. This is a 4-component system being proposed to solve a 1-step problem.

### 2b. Per-domain structure (crypto/, security/, ai-infra/) bakes in a taxonomy before any content exists.

Creating three domain directories before a single article exists is **structure-first design** — the exact anti-pattern Eric's steering rules warn against. Domains may not stay the same. Crypto and security overlap. "ai-infra" may be too narrow once investment research becomes a primary workflow.

### 2c. The overnight linting job has no defined benefit threshold.

What is the expected output? "Find inconsistencies and suggest improvements" is not a measurable deliverable. If the wiki has 8 articles, the linter will produce noise. This is the "Idle Is Success" doctrine applied in reverse — building a system that will generate output for the sake of generating output.

### 2d. Obsidian as viewer is an unasked-for UI dependency.

The proposal mentions Obsidian implicitly (via the Karpathy pattern). Jarvis already has jarvis-app. Adding Obsidian as a second knowledge viewer creates a fork in the UI strategy without a stated reason.

---

## 3. HIDDEN ASSUMPTIONS

### 3a. Assumes Eric will consistently ingest sources into raw/.

The ADHD pattern documented in memory (sporadic branching, mood-driven, tunnel vision) works directly against consistent raw/ maintenance. Karpathy's system works because he has the discipline (or automation) to file sources. If ingest is a manual step, the raw/ directory will be empty 90% of the time and stale 100% of the time.

### 3b. Assumes domain knowledge and process knowledge are separate and require separate systems.

Much of Eric's domain knowledge IS captured in synthesis — the April 3 synthesis already contains investment research patterns, architectural principles, and security conclusions. The assumption that these are categorically different and require a new system needs to be justified, not assumed.

### 3c. Assumes wiki articles will be more useful than synthesis documents.

Synthesis documents ARE compressed, cross-referenced knowledge. The proposal doesn't explain why wiki articles (which require a separate read path and UI) are better than synthesis for Q&A. The LLM can query synthesis directly.

### 3d. Assumes the bottleneck is knowledge retrieval.

The proposal never identifies a pain event: "I couldn't remember X because there was no wiki." Without a documented retrieval failure, this is a solution without a confirmed problem.

### 3e. Assumes /knowledge-query adds value over just asking the LLM directly.

In a solo operator context with relatively small corpora, "ask the LLM" already works. The additional retrieval layer only pays off when the corpus exceeds context window size. There is no evidence Eric is hitting that limit.

---

## 4. CATEGORY ERRORS

### 4a. Conflating "domain knowledge" with "research artifacts."

Research outputs (what /research produces) are **ephemeral work products**. Domain knowledge (what you know about crypto) is **distilled conclusions**. The proposal treats these as the same thing by filing both into raw/. They have different retention needs, different update frequencies, and different query patterns. Filing raw research into a wiki implies the wiki will be large, messy, and require curation — but curating is what synthesis already does.

### 4b. Conflating "knowledge base" with "memory system."

Jarvis already has a memory system. The proposal adds a second memory system with a different structure but overlapping purpose. This is not a clean new domain — it's an alternate implementation of what signals + synthesis already do for a different class of content. The correct question is: "Should synthesis handle domain knowledge?" not "Should we build a second system?"

### 4c. Conflating "overnight job" with "autonomous value production."

The proposal lists overnight linting as a feature. But linting an under-populated wiki generates alerts and suggestions with no one to act on them. The overnight runner's value comes from producing actionable outputs. Linting empty wiki articles produces noise. This confuses "we could run something at night" with "this would produce value at night."

---

## 5. REASONING FLAWS

### 5a. Excitement-driven, not pain-driven. (Motivated reasoning)

The proposal explicitly states: "inspired by seeing Karpathy's tweet." This is the canonical excitement trigger that Eric's steering rules are designed to intercept. The correct test: "What pain event does this solve?" is missing. The correct gate is /architecture-review, which was invoked — good. But the motivation should be named and accounted for in the decision.

### 5b. The existence of a gap does not justify this solution. (False dilemma framing)

"Research outputs are ephemeral" is a real gap. But the proposal jumps from that gap to a full wiki system without evaluating simpler solutions:
- Add a `--file` flag to /research that saves the output to memory/work/
- Extend synthesis to run against research outputs
- Add a "domain knowledge" section to existing synthesis documents

The alternatives section lists these but doesn't give them fair treatment — they're labeled as options without analyzing why the full wiki is needed over the simpler interventions.

### 5c. Survivorship bias on Karpathy's pattern.

Karpathy has the resources, tools, and workflow discipline to make this work. We're seeing the pattern, not the failure modes: what percentage of articles are stale? How much time does maintenance take? How often does he query it? The pattern is described as if it obviously works, but the evidence is one person's public description, not a validated outcome.

### 5d. The "richer over time" flywheel assumes consistent engagement. (Compounding fallacy)

"Outputs are filed back into the wiki, making it richer over time" describes a flywheel. Flywheels require consistent input. Eric's session patterns are sporadic. The wiki will have burst growth during periods of engagement and zero growth during quiet periods, resulting in a patchy, unevenly populated artifact — not a coherent knowledge base.

### 5e. Build cost is understated, maintenance cost is absent.

The proposal describes what gets built. It does not estimate:
- Time to build raw ingest pipeline + wiki recompilation
- Maintenance overhead (pruning stale articles, fixing broken backlinks)
- Cost of overnight linting job that runs on an under-populated wiki
- Migration cost if the taxonomy proves wrong

For a solo ADHD operator, underestimated maintenance is the #1 predictor of abandoned infrastructure.

---

## 6. WHAT IS SOUND

### 6a. The core gap is real: domain knowledge does not persist.

Process knowledge (what went wrong, what was learned about HOW to work) is well-served by signals + synthesis. Domain knowledge (what is known about DeFi liquidations, adversarial ML techniques, Claude API internals) is genuinely not captured. This is a legitimate gap worth solving.

### 6b. "File outputs" as a principle is correct.

The insight that /research outputs should not be ephemeral is sound. Filing conclusions into persistent storage, with some structure, is the right behavioral change regardless of implementation.

### 6c. LLM-compiled summaries are a valid pattern for this use case.

Having the LLM synthesize and compress research articles (rather than storing raw text) is appropriate for a solo operator. Raw text accumulation without synthesis is the wrong default — the proposal correctly identifies that LLM-compiled wiki articles are more queryable than raw clips.

### 6d. Domain separation (crypto, security, ai-infra) reflects real cognitive categories.

These are genuinely different domains with different source types, different update frequencies, and different query patterns. Some structure per domain makes sense. The implementation may be over-engineered, but the taxonomy is not wrong.

### 6e. Q&A against domain knowledge is a legitimate capability gap.

Eric currently cannot ask "what do I know about X?" and get a synthesized answer from his accumulated research. Adding this capability — in whatever form — is genuinely valuable, especially given the make-prediction use case where domain priors matter.

### 6f. Integration with make-prediction is the strongest use case.

The /make-prediction skill is explicitly identified as high-value (prediction philosophy memory entry). Domain priors fed from a knowledge layer would directly improve prediction quality. This is the sharpest concrete use case for the capability.

---

## VERDICT

**The gap is real. The solution is 3x too large.**

The minimum viable version of this capability:

1. Add `--save` to /research — files output to `memory/knowledge/{domain}/YYYY-MM-DD_{topic}.md`
2. Add a knowledge query step inside /make-prediction that scans the domain directory before prediction
3. No new overnight job, no wiki compilation, no Obsidian, no frontend view — not yet

Build the simplest version that captures outputs and makes them queryable. Evaluate for 30 days. If the corpus grows and retrieval becomes valuable, then design the wiki layer with real usage data. The Karpathy pattern is aspirational infrastructure for a corpus Eric doesn't have yet.

**One steering rule candidate**:
> When an external pattern inspires a new Jarvis layer, test the minimum-viable ingest path first (file the output) before building compilation, linting, or viewing infrastructure — corpus must exist before index is worth building.
