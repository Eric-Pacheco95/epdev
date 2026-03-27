# PRD: Phase 4 — Autonomous self-improvement & background Jarvis

> **Project:** epdev Jarvis  
> **Status:** planning  
> **Companion:** `orchestration/tasklist.md` Phase 4; `memory/work/jarvis/STATE.md`  
> **Slack policy:** `memory/work/slack-routing.md` — routine → `#epdev`; must-see → `#general` only.

## Mission

Jarvis must **self-improve** on purpose: not only react to human sessions, but run **isolated background automation** that (1) measures progress toward **ideal state**, (2) discovers improved patterns from **curated external sources** (web, GitHub, YouTube, Claude/Anthropic docs), and (3) **notifies Slack** by importance — learning opportunities, concrete improvements, and gap/regression signals — without spamming.

Human chat sessions remain the primary place for judgment and steering; background jobs **propose and measure**, they do not replace constitutional rules or irreversible actions without explicit human approval.

## Relationship to Phase 3

- **Phase 3E** defines the **heartbeat / ISC / gap → learning** spine (scheduled, repo-local, measurable).
- **Phase 4** adds **autonomous research & pattern harvesting**, **Karpathy-style bounded autoresearch** over internal knowledge (TELOS, signals, sessions), and tightens **notification semantics** so “progress toward ideal state” is visible even when you are not in a session.

## Karpathy autoresearch pattern (Jarvis adaptation)

[Karpathy’s autoresearch](https://github.com/karpathy/autoresearch) uses a **small, explicit contract**: fixed experiment budget, **one primary file the agent may edit** (`train.py` there), **`program.md` for human steering**, and a **single comparable metric** (e.g. validation loss). Jarvis does **not** adopt GPU training; it adopts the **control structure**:

| autoresearch (original) | Jarvis Phase 4 (adapted) |
|-------------------------|---------------------------|
| `program.md` — human-edited mission for the agent | `memory/work/jarvis/autoresearch_program.md` — scope, tone, what “better understanding” means |
| Agent edits `train.py` in bounded runs | Agent writes **only** to a **draft / run log tree** (e.g. `memory/work/jarvis/autoresearch/runs/`) — proposals, diffs, contradictions found — **never** direct edits to canonical TELOS |
| Fixed time budget per experiment | Fixed **steps per run** or **token budget** per scheduled invocation |
| Objective metric (val_bpb) | Jarvis-native metrics: e.g. **contradictions resolved**, **coverage** of TELOS pillars vs signals, **open questions** count, or checklist scores defined in `autoresearch_program.md` |

**Inputs to each autoresearch run (read-only for the agent):**

- **`memory/work/telos/`** — TELOS identity files (ground truth for “who Eric is” to the brain)
- **`memory/learning/signals/`** (and synthesis / failures as needed) — what learning-capture and the loop have accumulated
- **`memory/session/`** — recent session transcripts (bounded: last *n* files or date window) so iteration reflects actual dialogue, not only static docs

**Outputs:** Structured run artifacts (markdown/JSON), new **signals** with `Source: autonomous`, optional **`/telos-update`-style proposals** in a **review queue** — you (or a Claude Code session) **merge** into real TELOS and steering docs. Same rule as the rest of Phase 4: **no silent overwrite** of canonical identity.

## Architecture split (non-negotiable)

| Layer | Role | Examples |
|-------|------|----------|
| **OS scheduler** (Windows Task Scheduler primary) | Deterministic cadence, env secrets, repo writes, heartbeat | `python tools/scripts/jarvis_heartbeat.py`, future collectors |
| **Agentic / Cowork / Claude jobs** | Heavier analysis, summarization, “what should we adopt?” drafts | Curated feeds, digest prompts — **sandbox-aware**; no substitute for heartbeat truth on disk |
| **Human + Claude Code sessions** | Approve merges, new skills, steering rules, TELOS edits | `/learning-capture`, `/synthesize-signals`, `/update-steering-rules` |

Background jobs **must not** pretend to be interactive hooks; they write to **`memory/`**, **`history/`**, and optional queue files for later human review.

## Ideal State Criteria (ISC)

Each line is **eight words**, state-based, binary-testable.

- [ ] Background jobs avoid interactive human chat session runtime | Verify: job manifest + scheduler docs show separate triggers
- [ ] Heartbeat stores metric diff versus last baseline snapshot | Verify: `heartbeat_latest.json` and history log exist and parse
- [ ] Research outputs become signals or queued review artifacts | Verify: paths under `memory/learning/signals/` or `memory/work/jarvis/inbox/` with `Source: autonomous`
- [ ] Slack posts follow channel severity rules in slack-routing | Verify: routine → `C0ANZKK12CD`; critical → `C0AKR43PDA4` only when criteria met
- [ ] Autonomous jobs never execute arbitrary internet code downloads | Verify: PRD + constitutional rules; jobs read or analyze only
- [ ] Slack notifier respects daily cap per channel configuration | Verify: dedupe/cooldown logged or counted
- [ ] Autoresearch proposals queue before any TELOS file merge | Verify: only `memory/work/jarvis/autoresearch/**` writable by the loop; TELOS unchanged until human merge
- [ ] Autoresearch runs log input scope and metric snapshot | Verify: run artifact lists TELOS/signal/session slice and scores

Tag confidence: `[E]` where explicitly agreed here; `[I]` where implementation detail TBD.

## Scope

### 4A — Continuous ideal-state loop (extends 3E)

- Expand `jarvis_heartbeat` (or sibling collectors) toward **ISC-aligned metrics**: tests, signal counts, open tasks, security event counts, optional lint.
- **Gap → learning** when thresholds crossed: append structured signals (not raw spam).
- **Scheduler**: document Windows Task Scheduler tasks; optional stagger so heartbeat and research do not collide.

### 4B — Autonomous learning & research sessions

- **Goal:** Periodic jobs that pull **curated** sources (GitHub repos you allow-list, official docs, selected YouTube transcripts or summaries, blog feeds) and produce **short digests** + **candidate improvements** (new skills, patterns, tasklist suggestions).
- **Constraints:** Read-only or API-keyed fetch; **no** running install scripts from the network; **no** auto-commit to `main`; outputs are **drafts** in repo or signals until you approve in session.
- **Execution:** Prefer **dedicated** scheduled prompts (Cowork / headless Claude) **or** small Python fetch + LLM step on your machine — exact split TBD in implementation PRs.

### 4C — Slack notifications by importance

- **Routine progress / digest / heartbeat / “synthesis due”** → `#epdev`.
- **Must-see** (expired auth, security, irreversible block, sustained regression vs ISC) → `#general` per `slack-routing.md`.
- Implement **severity labels**, **deduplication**, and **cooldown** in notifier or wrapper script to avoid notification fatigue.

### 4D — Capstone: internal autoresearch loop (TELOS + learning + sessions)

> **Hard dependency:** Phase 3D "current vs ideal workflow" spec must exist before writing `autoresearch_program.md`. The program file cannot define meaningful metrics or scope without knowing how observed state maps to ideal state. Do not start 4D until 3D is complete.

**End state for Phase 4 implementation:** a **Jarvis autoresearch** subsystem that periodically (or on demand) **iterates** over:

1. TELOS files under `memory/work/telos/`
2. Learning artifacts from `/learning-capture` and related paths (`memory/learning/signals/`, synthesis, failures as configured)
3. **Session history** under `memory/session/` (time-bounded reads to control size)

… and produces **measurable improvement cycles**: proposed updates, identified gaps between TELOS and observed signals, session-derived insights — all landing in **`memory/work/jarvis/autoresearch/`** (runs, diffs, proposals) until reviewed.

**Deliverables (minimum):**

- `memory/work/jarvis/autoresearch_program.md` — human-steered charter (analogous to Karpathy’s `program.md`)
- Runner entrypoint (e.g. `tools/scripts/jarvis_autoresearch.py` or documented Cowork prompt + script) that enforces **read boundaries**, **write-only-to-autoresearch-tree**, and **run logging**
- **Success metric(s)** recorded per run (defined in program file; examples: contradiction count, “unresolved question” list length, checklist pass rate)
- Optional Slack summary to `#epdev` when a run finds high-impact proposals or metric deltas

**Explicitly out of scope for the agent:** direct writes to `memory/work/telos/*.md` except via human-approved merge from the review queue.

## Phase 5 preview (Daemon-inspired behavioral change)

Phase 5 is a separate PRD (`memory/work/jarvis/PRD_phase5.md`) to be written after Phase 4 is substantially complete. The concept: close the loop from system improvement → human behavior. Jarvis observes gaps between TELOS goals (guitar, health, financial, self-discovery) and actual session/signal evidence, then proposes concrete behavioral actions — not system improvements. Miessler's forthcoming "Daemon" project is the inspiration. Phase 5A is exploration-first: define what behavioral change means for Jarvis before building anything.

## Non-goals (Phase 4)

- Replacing human approval for merges, secrets, or production changes.
- Unbounded open-web scraping without allow-lists and rate limits.
- Fully autonomous TELOS rewrites without review.

## Open decisions

- Allow-list format for URLs/repos (`memory/work/jarvis/sources.yaml` TBD).
- Whether research runs weekly vs daily; cost and noise tradeoffs.
- ntfy integration for mobile push (may remain Phase 3B/3E overlap).
- Voice sessions (Phase 3C) produce signals with `Source: voice` — autoresearch should include voice signals in its read scope once Phase 3C Layer 1 is live. See `memory/work/jarvis/PRD_voice_mobile.md`.

## References

- [karpathy/autoresearch](https://github.com/karpathy/autoresearch) — inspiration for bounded agent loops and human-steered `program.md` (Jarvis adapts the **pattern**, not ML training)
- `tools/scripts/jarvis_heartbeat.py` — current heartbeat implementation
- `memory/work/slack-routing.md` — channel IDs and rules
- `security/constitutional-rules.md` — untrusted input, no secret leakage
- `orchestration/tasklist.md` — Phase 3E + Phase 4 task breakdown

Last updated: 2026-03-26
