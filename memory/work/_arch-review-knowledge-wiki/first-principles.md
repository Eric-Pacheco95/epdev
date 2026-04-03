# First-Principles Analysis: LLM-Compiled Knowledge Wiki
- Date: 2026-04-03
- Analyst: Architecture Review Agent (Sonnet 4.6)
- Proposal: Add Karpathy-style knowledge wiki layer to Jarvis memory system
- Method: First-principles decomposition — strip framing, challenge assumptions, find simplest viable path

---

## 1. What Is The Fundamental Problem Being Solved?

Strip away the Karpathy framing entirely. What is the actual, irreducible problem?

**The stated complaint:** `/research` outputs are ephemeral. Knowledge gained from web research disappears between sessions. Over time Eric researches the same domains (crypto, security, AI infra) repeatedly without building a compounding knowledge base.

**The real problem decomposed:**

**Problem A — Knowledge loss between sessions.** When `/research` produces a brief, that knowledge is written to `memory/work/{slug}/research_brief.md` but never synthesized, cross-linked, or made queryable. The next `/research` on a related topic starts from scratch.

**Problem B — No accumulated domain model.** Eric has process knowledge (signals/synthesis) but no domain model. "What do I actually know about crypto trading?" has no answer the system can give. The knowledge lives in scattered briefs and in Eric's head.

**Problem C — Research retrieval friction.** To find what was previously researched, Eric must remember a slug name and navigate files. There is no "query my knowledge base" capability.

**Problem D — No quality feedback loop on research.** No mechanism catches contradictions between briefs, identifies stale data, or surfaces "you researched this before but got a different answer."

**Verdict:** Problem A is real and the primary gap. Problem B is real but lower-frequency (how often does Eric ask "what do I know about X?"). Problem C is moderate friction. Problem D is a nice-to-have that does not block actual work.

The Karpathy framing bundles all four into one solution that also adds: raw/ ingest, wiki compilation, Obsidian viewing, Q&A routing, linting, a brain-map view, and two new skills. **The proposal is solving Problems A-D plus adding capabilities nobody asked for.**

---

## 2. What Are The Irreducible Requirements?

Minimum requirements for solving Problem A (the core gap):

1. Research output must persist beyond the session that produced it, in a form that is retrievable without knowing the exact file path.
2. A new research session on a related topic must be able to see prior relevant findings before searching the web again.
3. The storage format must be writable by existing Jarvis skills without introducing new tooling.
4. The retrieval mechanism must work inside a Claude Code session (no external database process required).

Requirements that are NOT irreducible (they are nice-to-have features, not hard requirements):
- Obsidian compatibility
- Backlinks between articles
- Dedicated `raw/` ingest pipeline
- LLM "linting" of inconsistencies
- Brain-map frontend view
- Separate `knowledge/` directory tree

---

## 3. Assumptions In The Proposal That May Be Wrong

**Assumption 1: Domain knowledge requires a different directory structure than learning knowledge.**

Challenge: The existing `memory/learning/` system already stores and synthesizes signals. The reason it cannot store domain knowledge is not architectural — it is definitional. A "signal" is a process observation. A "synthesis" is a distillation of signals. But there is nothing structurally preventing a synthesis document from being a domain knowledge article instead of a process theme article. The synthesis machinery already does the right thing — it reads a set of inputs and produces a structured summary. The assumption that domain knowledge needs its own directory tree is likely wrong.

**Assumption 2: A `raw/` ingest directory is needed.**

Challenge: The existing `/research` skill already handles the "raw source" step. It fetches from the web, rates sources, extracts content. The output brief is already the synthesized form of the raw content. A `raw/` directory would hold... articles that Claude already read and summarized. Storing raw HTML/markdown before LLM compilation duplicates what Tavily already does. The only case where `raw/` adds value is when Eric clips sources manually (Readwise, browser extension). That is a niche workflow that should not drive the architecture.

**Assumption 3: The Karpathy pattern applies to a personal AI brain the same way it applies to a personal knowledge base.**

Challenge: Karpathy's pattern is designed for a human who reads and manually clips sources over months, building a knowledge base that eventually becomes queryable. Jarvis already has automated research via `/research` + Tavily. The compilation step (raw -> wiki) is already happening inside the skill. What Karpathy's pattern adds for a human — LLM assistance in making sense of manually gathered sources — Jarvis does not need because Jarvis already applies LLM synthesis at collection time. Applying the pattern wholesale imports unnecessary ceremony for a different use case.

**Assumption 4: Obsidian is the right viewer.**

Challenge: Jarvis already has a brain-map dashboard (React). Adding Obsidian as a viewer means maintaining a second frontend dependency and ensuring markdown file conventions match Obsidian's link format. The existing brain-map is already the correct integration point. This assumption likely reflects "Obsidian is cool" rather than "Obsidian solves a specific problem Jarvis has."

**Assumption 5: Wiki compilation is a separate overnight job.**

Challenge: If wiki compilation happens overnight, it is always one day behind. But Eric's research sessions are interactive. The value of "what did I previously find about this?" is highest immediately, not the next morning. A nightly linting pass is reasonable, but the compilation (brief -> knowledge article) should happen at research time, not overnight.

**Assumption 6: Two new skills are needed.**

Challenge: The existing `/research` skill already handles research execution. The existing `/synthesize-signals` (or equivalent) handles distillation. The gap is not missing skills — it is that `/research` output does not feed into the memory system, and there is no retrieval path before search. Both are configuration/output-routing changes to existing skills, not new skill definitions.

---

## 4. What Is The Simplest Architecture That Satisfies The Requirements?

**The reducible requirements again:**
1. Research persists and is retrievable without exact path knowledge
2. New research can see prior relevant findings
3. No new tooling required
4. Works inside Claude Code session

**Simplest solution: Extend `/research` output routing + add a knowledge index**

### Step 1: Research Brief Persistence (already almost working)

`/research` already writes briefs to `memory/work/{slug}/research_brief.md`. The gap is that these are isolated per-project with no cross-domain discoverability. Fix: add a research registry file.

**File: `memory/knowledge_index.md`**

A flat registry (like `MEMORY.md` but for domain knowledge) that `/research` appends to after every brief:

```markdown
## Crypto
- 2026-03-15 | crypto-trading-bot-landscape | memory/work/crypto-trading-bot/research_brief.md | key finding: X
- 2026-04-01 | btc-etf-flows-q1 | memory/work/btc-etf-q1/research_brief.md | key finding: Y

## Security
- 2026-03-20 | prompt-injection-patterns | memory/work/prompt-injection/research_brief.md | key finding: Z
```

Cost: 3 lines added to `/research` Step 3 (append domain + one-liner to index).

### Step 2: Pre-Search Retrieval (the real value-add)

At the start of `/research` Phase 1, before generating sub-questions, read `memory/knowledge_index.md` and check for domain overlap. If prior briefs exist on the same domain, load the most recent 1-2 and surface their key findings. This replaces "start from scratch" with "here is what we previously found."

Cost: 5-10 lines added to `/research` Phase 0.

### Step 3: Domain Synthesis (replaces wiki compilation)

The existing `synthesize-signals` pattern already does themed distillation. Add a periodic domain knowledge synthesis that reads all briefs in a domain and produces a `memory/knowledge/{domain}/summary.md`. This is structurally identical to the existing synthesis flow — it just reads from `memory/work/*/research_brief.md` instead of `memory/learning/signals/`.

Cost: One new overnight job configuration (small). No new directory structure beyond `memory/knowledge/{domain}/`.

### What this does NOT include (deliberately omitted):
- `raw/` directory — Tavily is the raw layer; raw clips can go into `memory/work/{slug}/sources/` if ever needed
- Obsidian — brain-map is the viewer
- Wiki backlinks — overkill for a solo operator; knowledge_index.md provides discoverability
- LLM linting pass — add only when inconsistency is actually a felt problem
- `/research-ingest` skill — not needed; `/research` already handles ingest
- `/knowledge-query` skill — not needed yet; existing read + context is sufficient

---

## 5. Does The Existing System Already Solve This?

**Partial solve — closer than the proposal implies:**

| Requirement | Existing Coverage | Gap |
|---|---|---|
| Research persistence | Yes — briefs written to `memory/work/` | Gap: no index, no cross-domain discoverability |
| Prior knowledge retrieval | No | Gap: `/research` starts fresh every time |
| Domain synthesis | No dedicated mechanism | Gap: synthesis runs on signals, not research briefs |
| Contradiction detection | No | Not a felt pain yet; defer |
| Queryable knowledge | Partial — briefs readable if path known | Gap: requires path knowledge |

The system is about 40% of the way there. The remaining 60% is output routing and a flat index — not a new architectural layer.

**The proposal adds 200% of the complexity needed to close a 60% gap.** That ratio is the primary signal that the Karpathy framing has imported significant ceremony.

---

## 6. Is There A Simpler Path That Achieves 80% Of The Value?

Yes. The 80% path:

**Phase 1 (low effort, high value — implement now):**
1. Add `memory/knowledge_index.md` — flat registry by domain. `/research` appends after every brief. (`~30 min`)
2. Modify `/research` Phase 0 to read the index and surface prior findings before searching. (`~1 hour`)

**This alone closes Problem A (knowledge loss) and Problem C (retrieval friction).** No new directory structure. No new skills. No new tooling. Two targeted edits to one existing skill.

**Phase 2 (medium effort, medium value — do when Phase 1 is validated):**
3. Add domain synthesis to the overnight runner: read all briefs per domain, produce `memory/knowledge/{domain}/summary.md`. Reuse the existing synthesis prompt pattern. (`~2 hours`)

**This closes Problem B (no accumulated domain model).**

**Phase 3 (defer until felt as pain):**
4. LLM linting / contradiction detection — only when Eric notices contradictions between briefs that cost him time.
5. Brain-map knowledge browser — only when the knowledge base is large enough to need visual navigation (threshold: 20+ domain articles).

**What to never build:**
- `raw/` ingest directory (Tavily handles it)
- Obsidian integration (brain-map is the viewer)
- `/research-ingest` as a separate skill (absorb into `/research`)
- `/knowledge-query` as a separate skill (absorb into `/research` Phase 0)

---

## Summary Verdict

| Dimension | Proposal | Simple Path |
|---|---|---|
| New directory depth | 3 levels (`knowledge/crypto/raw/`) | 1 level (`knowledge/crypto/`) or flat index |
| New skills | 2 (`/research-ingest`, `/knowledge-query`) | 0 (extend `/research`) |
| New overnight jobs | 1 (wiki compilation + linting) | 1 (domain synthesis only) |
| New tooling | Obsidian | None |
| Value delivered | ~90% | ~80% |
| Effort | High | Low-Medium |
| Reversibility | Low (new structure bakes in) | High (index file, skill edits) |
| Steering rule alignment | Violates "absorb ideas over adopt dependencies" | Compliant |

**Recommendation: Do not build the proposal as specified.** Execute Phase 1 (knowledge index + pre-search retrieval) immediately — it is the highest-value, lowest-effort change and validates whether the gap is real. If Eric starts research sessions saying "thanks for showing me what we already know," Phase 2 (domain synthesis) is justified. The Karpathy wiki architecture is the right north star for a public or team knowledge base; for a solo personal AI brain where LLM synthesis already happens at collection time, it imports unnecessary structure.

**The genuine insight from Karpathy's pattern:** The LLM should maintain a running, structured knowledge base, not just ephemeral per-session briefs. That insight is correct. The specific mechanism (raw/ + wiki + Obsidian + compilation jobs) is optimized for a different workflow.

---

## Decision Log

- Recommendation: Implement Phase 1 only (knowledge_index.md + `/research` Phase 0 modification)
- Defer: Phase 2 (domain synthesis) pending Phase 1 validation
- Reject: Raw directory, Obsidian, new skills, frontend view (at this stage)
- Confidence: High — three independent threads (existing system audit, requirements decomposition, assumption challenge) converge on same minimal path
- Next step: If Eric approves, modify `/research` SKILL.md to add index append (Step 3) and prior-knowledge lookup (Phase 0), then create `memory/knowledge_index.md` as empty template
