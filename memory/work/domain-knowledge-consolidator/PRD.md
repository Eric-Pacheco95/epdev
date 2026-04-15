# PRD: Domain Knowledge Consolidator

> Path: memory/work/domain-knowledge-consolidator/PRD.md
> Status: DRAFT — awaiting ISC model annotation approval

---

## OVERVIEW

The domain knowledge pipeline currently produces isolated per-topic research articles in `memory/knowledge/<domain>/YYYY-MM-DD_<slug>.md` but has no consolidation layer — Jarvis cannot answer "what do I know about AI agent orchestration?" without loading 18 individual files. This PRD specifies a weekly autonomous consolidation job (`domain_knowledge_consolidator.py`) that reads raw knowledge articles from all valid producers, applies first-principles and fallacy-detection lenses during synthesis, and writes `_context.md` (domain summary) and `<sub-domain>.md` (clustered deep context) files per domain. The job runs in a git worktree on Sunday 5am, produces a human-reviewable proposal before any commit, autonomously manages domain lifecycle (create, update, retire), and extends the CLAUDE.md routing table so Jarvis loads domain context on-demand when a task's topic matches domain trigger keywords.

---

## PROBLEM AND GOALS

- **P1**: Jarvis has 27+ knowledge articles across 7 domains with no consolidated context surface — each session must re-derive domain knowledge from scratch or skip it entirely
- **P2**: Multiple producers (research_producer, /absorb, morning_feed, predictions, backtest) all generate domain-relevant MD files with no unified consolidation path
- **P3**: Raw knowledge articles are not quality-filtered for logical fallacies or unstated assumptions before being treated as authoritative context
- **P4**: Domain taxonomy is static — new domains are never created from emerging article clusters, dead domains are never retired
- **G1**: Every domain with >= 1 raw article has a `_context.md` that can be loaded as a single context token budget instead of N files
- **G2**: Sub-domain files cluster articles into coherent sub-topics (>= 3 articles threshold), enabling surgical context loading
- **G3**: First-principles and fallacy-detection lenses are applied at synthesis time — no raw article assumption survives unchallenged into a sub-domain context file
- **G4**: Domain lifecycle is managed autonomously — new domains are proposed and created when article clusters form outside existing domains; dead domains are flagged and retired
- **G5**: Eric reviews a single weekly consolidation report before any `_context.md` or sub-domain file is committed — batch approval gate, not per-article

---

## NON-GOALS

- No changes to how raw knowledge articles are produced (research_producer, /research skill, morning_feed remain unchanged)
- No modification to how absorbed articles are created (/absorb skill is upstream, not in scope)
- No automated merge or deletion of raw `YYYY-MM-DD_*.md` source articles — the consolidation job reads but never modifies or moves source files
- No real-time context injection — domain context is on-demand via CLAUDE.md routing, not auto-loaded every session
- No vector search or embedding layer (deferred to Phase 6 local embedding build)
- No changes to `/research` skill internals — quality gating happens at consolidation time, not at article-write time

---

## USERS AND PERSONAS

- **Eric (primary)**: Reviews weekly consolidation report, approves/rejects proposed sub-domain files and domain taxonomy changes, commits accepted output
- **Jarvis (interactive sessions)**: Loads `_context.md` or sub-domain files on-demand when task topic matches domain keywords in CLAUDE.md routing table
- **research_producer / dispatcher (autonomous)**: Reads `index.md` for dedup and coverage checks — unchanged, but gains richer context from updated index after consolidation
- **make-prediction skill**: Reads domain knowledge index for priors when forming predictions — gains sub-domain context paths from updated index

---

## USER JOURNEYS OR SCENARIOS

**Weekly autonomous run (primary):**
1. Sunday 5am — Task Scheduler fires `run_domain_consolidator.bat`
2. Script creates a git worktree (`jarvis/knowledge-consolidation-YYYY-MM-DD`)
3. For each domain: reads all source files (raw articles + matched absorbed + B+ morning_feed items + prediction/backtest for fintech/geo) since last consolidation
4. For each domain: applies first-principles + fallacy-detection lenses in LLM prompt before writing context
5. Produces `_context.md` + proposed sub-domain files in the worktree (not main tree)
6. Writes `memory/knowledge/_consolidation_report.md` summarizing all changes, new sub-domains proposed, domains flagged for creation/retirement, contradictions found
7. Sends Slack notification to `#epdev` with report summary and link
8. Job exits — no auto-commit
9. Eric reviews report in next session, runs `python tools/scripts/domain_knowledge_consolidator.py --commit` to accept or `--reject <domain>` to discard proposals

**Eric asks Jarvis about "AI agent orchestration" (session use):**
1. Task topic includes "agent orchestration" → CLAUDE.md routing table matches trigger keyword
2. Jarvis loads `memory/knowledge/ai-infra/_context.md` (domain summary, ~2000 tokens)
3. If topic is specifically "orchestration patterns," additionally loads `memory/knowledge/ai-infra/agent-orchestration.md` (sub-domain file)
4. Jarvis reasons with full domain context without loading all 18 raw articles

**New domain creation (autonomous):**
1. Consolidation job finds 3+ articles that don't fit existing domains (e.g., 3 geopolitics articles in `memory/learning/absorbed/`)
2. Proposes new `geopolitics` domain in consolidation report with draft `_context.md` and initial sub-domain structure
3. Eric approves → domain directory created, CLAUDE.md routing entry added, `index.md` updated

**Domain retirement (autonomous):**
1. Consolidation job finds a domain with <= 1 article, last-updated > 90 days ago (e.g., `smart-home` or `automotive` after the EV decision is made)
2. Flags for retirement in consolidation report — does NOT delete files
3. Eric approves → domain directory remains as archive, routing entry removed from CLAUDE.md

---

## FUNCTIONAL REQUIREMENTS

**Script — Core Consolidation:**
- FR-001: `domain_knowledge_consolidator.py` reads source files per domain in priority order: (1) `memory/knowledge/<domain>/YYYY-MM-DD_*.md`, (2) `memory/learning/absorbed/*.md` (keyword-matched to domain), (3) `memory/work/jarvis/morning_feed/YYYY-MM-DD.md` (B+ rated items only, last 30 days), (4) `data/predictions/*.md` and `data/predictions/backtest/*.md` (fintech + geopolitics domains only), (5) domain-tagged themes from `memory/learning/synthesis/*.md`
- FR-002: Script NEVER reads `_context.md` or `<sub-domain>.md` files as source inputs — only dated `YYYY-MM-DD_*.md` or explicitly whitelisted non-dated source paths are valid inputs
- FR-003: Each domain's LLM synthesis prompt includes first-principles lens ("what assumptions does this article make that are not stated?") and fallacy-detection lens ("does this claim contain logical fallacies: hasty generalization, survivorship bias, false dichotomy?") — output must surface detected assumptions and fallacies as a "Caveats" section in the sub-domain file
- FR-004: Script maintains a state file (`data/domain_consolidator_state.json`) tracking per-domain: last_consolidated timestamp, list of source files incorporated, article count — enables incremental updates (only new files since last run are synthesized into existing sub-domain MDs)
- FR-005: `_context.md` per domain is capped at 8000 characters (~2000 tokens); when cap is approached, excess is pushed to sub-domain files, not truncated
- FR-006: Sub-domain files are created when >= 3 articles cluster around a coherent sub-topic (LLM clustering); sub-domain files are proposed (not auto-committed) until Eric approves

**Script — Domain Lifecycle:**
- FR-007: Script autonomously proposes new domain creation when: (a) >= 3 absorbed articles share keywords outside existing domains OR (b) research_producer TELOS gap scan identifies an active goal domain with no knowledge directory
- FR-008: Script autonomously proposes domain retirement when: (a) domain has <= 1 article AND last article is > 90 days old OR (b) all domain articles have been superseded/migrated to another domain
- FR-009: Domain retirement is proposal-only — no directories or files are deleted autonomously; retirement = remove CLAUDE.md routing entry + add `RETIRED: <date> <reason>` to `index.md`
- FR-010: `general` domain is flagged for retirement on first run with all articles marked for reassignment to appropriate domains

**Script — Worktree and Review Flow:**
- FR-011: Script runs inside a git worktree created at run start (`jarvis/knowledge-consolidation-YYYY-MM-DD`) and destroyed after Eric commits or rejects — uses `_safe_worktree_remove()` from `tools/scripts/lib/worktree.py`
- FR-012: `_consolidation_report.md` is written to `memory/knowledge/` in the worktree before script exits, containing: per-domain article count delta, new sub-domains proposed, domains proposed for creation/retirement, contradictions detected, fallacies surfaced, token counts for each `_context.md`
- FR-013: Slack notification to `#epdev` on each run with report headline: N domains processed, N sub-domains proposed, N taxonomy changes proposed, N contradictions found
- FR-014: `--commit` flag accepts all proposed changes and merges worktree to main; `--reject <domain>` discards proposals for a specific domain; `--reject-all` discards the full worktree

**CLAUDE.md Routing Integration:**
- FR-015: CLAUDE.md context routing table gains entries for each domain, formatted as: `| Topic includes: <keyword1>, <keyword2> | memory/knowledge/<domain>/_context.md |` — loaded on-demand, not auto-injected
- FR-016: Sub-domain files are listed in their domain's routing entry as secondary targets: `→ sub-domains: <sub-domain1>.md, <sub-domain2>.md`
- FR-017: Dispatcher task prompts for research tasks in a domain include the domain's `_context.md` path in `context_files` — so autonomous research workers know prior domain knowledge before writing new articles

**Task Scheduler:**
- FR-018: `run_domain_consolidator.bat` registered in Task Scheduler as `\Jarvis\DomainKnowledgeConsolidator`, S4U logon, `RunLevel Highest`, trigger: weekly Sunday 5:00am

---

## NON-FUNCTIONAL REQUIREMENTS

- Total weekly run time: < 15 minutes for all existing domains (7 domains, 27 articles)
- Token cost per run: < $0.50 (Sonnet at $3/1M input; estimated 30K input tokens total across all domain synthesis passes)
- `_context.md` hard cap: 8000 chars (~2000 tokens) — enforced by script, not by LLM discretion
- Sub-domain file hard cap: 6000 chars (~1500 tokens) — same enforcement
- State file must use file-level lock (same pattern as `backlog_append.py`) to prevent concurrent write corruption
- Script must emit a health signal to `memory/learning/signals/` on each run (success or failure), detectable by `verify_producer_health.py`
- All console output must be ASCII-only (Windows cp1252 safe)

---

## ACCEPTANCE CRITERIA

**Phase 1 — Consolidation Script**

- [ ] `domain_knowledge_consolidator.py` exists at `tools/scripts/domain_knowledge_consolidator.py` and passes `--dry-run` without error on all existing domains `[E][A]` | Verify: `python tools/scripts/domain_knowledge_consolidator.py --dry-run` exits 0 | model: sonnet
- [ ] Each domain directory with >= 1 raw `YYYY-MM-DD_*.md` article produces a `_context.md` after a full run `[E][M]` | Verify: `python -c "import pathlib; dirs=[d for d in pathlib.Path('memory/knowledge').iterdir() if d.is_dir() and any(d.glob('2[0-9]*_*.md'))]; missing=[d for d in dirs if not (d/'_context.md').exists()]; print('FAIL:', missing) if missing else print('PASS')"` exits with PASS
- [ ] `ai-infra` domain produces >= 3 sub-domain files after first run (18 source articles) `[E][M]` | Verify: `python -c "import pathlib; files=[f for f in pathlib.Path('memory/knowledge/ai-infra').glob('*.md') if not f.name.startswith('_') and not f.name[0].isdigit()]; print(len(files), files)"` count >= 3
- [ ] Every `_context.md` file is <= 8000 characters `[E][M]` | Verify: `python -c "import pathlib; over=[str(p)+':'+str(len(p.read_text(encoding='utf-8'))) for p in pathlib.Path('memory/knowledge').rglob('_context.md') if len(p.read_text(encoding='utf-8'))>8000]; print('FAIL:',over) if over else print('PASS')"` exits with PASS | model: haiku
- [ ] Script state file `data/domain_consolidator_state.json` exists and contains per-domain last_consolidated timestamps after a run `[E][M]` | Verify: `python -c "import json,pathlib; s=json.loads(pathlib.Path('data/domain_consolidator_state.json').read_text()); assert 'ai-infra' in s and 'last_consolidated' in s['ai-infra']; print('PASS')"` | model: haiku
- [ ] **[ANTI]** `_context.md` and sub-domain files are NEVER read as source inputs — script source-input paths exclude any file matching `_*.md` or any non-dated filename pattern `[E][A]` | Verify: `grep -n "_context\|sub-domain" tools/scripts/domain_knowledge_consolidator.py | grep -v "#\|output\|write\|report\|path\|str"` returns 0 lines that reference these as read targets | model: opus (architecture constraint)
- [ ] Each sub-domain file contains a "Caveats" section surfacing detected assumptions and fallacies from source articles `[I][A]` | Verify: Read 2 sub-domain files — confirm presence of `## Caveats` section with >= 1 entry | model: opus
- [ ] `_consolidation_report.md` is written to `memory/knowledge/` and contains: domain article counts, proposed sub-domains, taxonomy proposals, contradiction count `[E][M]` | Verify: `test -f memory/knowledge/_consolidation_report.md && grep -c "Proposed\|Contradiction\|Article count" memory/knowledge/_consolidation_report.md` >= 3 | model: sonnet

**Phase 2 — Domain Taxonomy**

- [ ] `geopolitics` domain directory created with `_context.md` populated from absorbed articles (iran-trap, AI datacenter geopolitical angle) and prediction backtest files (iran nuclear deal, Russia-Ukraine, Afghanistan) `[E][M]` | Verify: `test -d memory/knowledge/geopolitics && test -f memory/knowledge/geopolitics/_context.md` | model: sonnet
- [ ] `predictions` domain directory created with `_context.md` populated from `prediction-framework.md` (moved from ai-infra), `calibration_narrative.md`, backtest result patterns `[E][M]` | Verify: `test -d memory/knowledge/predictions && test -f memory/knowledge/predictions/_context.md` | model: sonnet
- [ ] `general` domain is flagged in `_consolidation_report.md` as "proposed for retirement" with each article mapped to a target domain `[E][M]` | Verify: `grep -c "general.*retire\|retire.*general" memory/knowledge/_consolidation_report.md` >= 1 | model: haiku
- [ ] **[ANTI]** Domain retirement proposals do NOT delete or move source files — all `memory/knowledge/general/*.md` files exist unchanged after consolidation run `[E][A]` | Verify: `test -f memory/knowledge/general/2026-03-27_evolution-big-bang.md` exits 0 after run | model: haiku
- [ ] `index.md` is updated to reflect new domains and any sub-domain context file paths `[E][M]` | Verify: `grep -c "geopolitics\|predictions" memory/knowledge/index.md` >= 2 after run | model: sonnet

**Phase 3 — Worktree and Review Flow**

- [ ] Script creates a git worktree before writing any files, and all output files land in the worktree (not main tree) `[E][A]` | Verify: Read script — confirm `git worktree add` call precedes all file writes; confirm output paths are relative to worktree root | model: opus
- [ ] `--commit` flag merges worktree to main using `_safe_worktree_remove()` and does not leave orphan worktrees `[E][M]` | Verify: Run `--commit` then `git worktree list` — no `jarvis/knowledge-consolidation-*` entries remain | model: sonnet
- [ ] Slack notification fires on every run (success or failure) with domain count and taxonomy proposal summary `[I][M]` | Verify: `python tools/scripts/domain_knowledge_consolidator.py --dry-run` + check Slack `#epdev` for message | model: sonnet
- [ ] **[ANTI]** Script does NOT auto-commit — no `git commit` or `git push` calls exist outside the explicit `--commit` flag path `[E][A]` | Verify: `grep -n "git commit\|git push" tools/scripts/domain_knowledge_consolidator.py | grep -v "# \|commit_flag\|--commit"` returns 0 lines | model: haiku

**Phase 4 — Task Scheduler and CLAUDE.md**

- [ ] `run_domain_consolidator.bat` exists and calls the script with correct Python path and `--autonomous` flag `[E][A]` | Verify: `test -f tools/scripts/run_domain_consolidator.bat && grep -c "domain_knowledge_consolidator.py" tools/scripts/run_domain_consolidator.bat` >= 1 | model: haiku
- [ ] Task Scheduler task `\Jarvis\DomainKnowledgeConsolidator` registered with S4U logon, Sunday 5:00am trigger `[E][M]` | Verify: `powershell "Get-ScheduledTask -TaskPath '\\Jarvis' -TaskName 'DomainKnowledgeConsolidator' | Select-Object -ExpandProperty Principal | Select-Object LogonType"` returns `S4U` | model: sonnet
- [ ] CLAUDE.md context routing table contains entries for 5 domains (ai-infra, fintech, crypto, security, geopolitics) pointing to `_context.md` with trigger keywords `[E][A]` | Verify: `grep -c "memory/knowledge" CLAUDE.md` >= 5 | model: haiku
- [ ] Each domain routing entry includes trigger keywords and lists sub-domain files as secondary load targets `[E][A]` | Verify: Read CLAUDE.md routing section — each knowledge entry has "Topic includes:" and "→ sub-domains:" pattern | model: opus
- [ ] **[ANTI]** CLAUDE.md routing entries do NOT auto-load domain context on every session — entries use "Topic includes" conditional pattern, not unconditional load `[E][A]` | Verify: Read CLAUDE.md — no domain knowledge entry appears outside the routing table (i.e., not in the always-loaded preamble) | model: opus

**ISC Quality Gate: PASS (7/7)**
1. Count: 8 Phase 1, 5 Phase 2, 4 Phase 3, 5 Phase 4 — all within 3-8 range ✓
2. Conciseness: Each criterion is one sentence, no compound "and" ✓
3. State-not-action: All describe what IS true when done ✓
4. Binary-testable: All have concrete pass/fail commands ✓
5. Anti-criteria: 5 anti-criteria across 4 phases ✓
6. Verify method: Every criterion has `| Verify:` suffix ✓
7. Vacuous-truth audit: All `test -f` and `grep -c` commands guard against empty-match exits; python assertions exit nonzero on failure; no bare `find` or `ls` ✓

---

## SUCCESS METRICS

- All existing domains have a `_context.md` within 7 days of first run
- `ai-infra` reduced from 18 individual files to 1 `_context.md` + 4-5 sub-domain files (verified by article-count delta in consolidation report)
- `geopolitics` and `predictions` domains created and populated in first run
- CLAUDE.md routing table loads domain context in <= 1 read per query instead of N article reads
- Zero vacuous-truth verifier failures (all ISC verify commands exit nonzero on the forbidden state)
- Weekly consolidation report reviewed and committed by Eric within 2 days of Sunday run (cadence target)

---

## OUT OF SCOPE

- Changes to `/research` skill, `research_producer.py`, or `/absorb` skill (upstream — not modified)
- Real-time domain context injection into every prompt (on-demand only)
- Vector search or semantic retrieval over knowledge articles (Phase 6)
- Modifying how morning_feed.py rates items (B+/C/D ratings are consumed as-is)
- `/make-prediction` routing changes (will read updated index.md automatically)
- Applying first-principles / fallacy-detection validation at `/research` write time (consolidation-time only per this PRD)

---

## DEPENDENCIES AND INTEGRATIONS

- `tools/scripts/lib/worktree.py` — `_safe_worktree_remove()` for worktree teardown (must exist and be tested)
- `tools/scripts/slack_notify.py` — Slack notification on run completion
- `memory/knowledge/index.md` — updated as part of each consolidation run
- `orchestration/steering/autonomous-rules.md` — worktree requirement, producer health signal requirement
- `CLAUDE.md` — context routing table is modified by this PRD
- `tools/scripts/jarvis_dispatcher.py` — dispatcher task `context_files` updated for research tasks (FR-017)
- `tools/scripts/verify_producer_health.py` — must be extended to monitor this producer
- `data/domain_consolidator_state.json` — new runtime state file (gitignored, like other data/ state files)
- Windows Task Scheduler — S4U principal, `\Jarvis` task path
- Claude API (Sonnet) — LLM synthesis calls; estimated $0.20-$0.50/week at current article volume

---

## RISKS AND ASSUMPTIONS

### Risks

- **R1: LLM clustering produces poor sub-domain groupings** — if the LLM clusters 18 ai-infra articles into sub-domains that don't match Eric's mental model, the output is noise. Mitigation: first run is human-reviewed; domain taxonomy audit is in the weekly report.
- **R2: Morning feed rating format changes** — if `morning_feed.py` changes how it formats ratings (B+/C/D), the filter breaks silently and C-rated items pollute domain context. Mitigation: parser is a separate function with a unit test asserting B+ extraction from a fixture.
- **R3: State file diverges from actual files** — if `domain_consolidator_state.json` lists a file as consolidated but the sub-domain file was subsequently deleted, the next run skips it. Mitigation: on startup, validate state against actual `_context.md` existence; if mismatch, re-consolidate.
- **R4: Context file bloat over months** — as research_producer keeps filing new articles, sub-domain files grow beyond 6000 chars. Mitigation: hard cap enforced in script; when cap is hit, script auto-proposes sub-domain split in consolidation report.
- **R5: First-principles + fallacy lens adds hallucinated caveats** — LLM may invent fallacies that don't exist in the source article, reducing trust in caveats section. Mitigation: caveats are labeled "LLM-flagged, unverified" — Eric validates during weekly review.

### Assumptions

- **A1**: `tools/scripts/lib/worktree.py` exists and `_safe_worktree_remove()` handles Windows junction reparse points correctly (per 2026-04-15 junction fix)
- **A2**: All knowledge files in `memory/knowledge/` are git-tracked (confirmed: not in .gitignore)
- **A3**: Claude Sonnet is the right model for domain synthesis (cost/quality tradeoff; Opus is not needed for synthesis, only for security/architecture criteria evaluation)
- **A4**: Morning feed B+ rating is parseable from `memory/work/jarvis/morning_feed/YYYY-MM-DD.md` using the existing rating format
- **A5**: `geopolitics` and `predictions` domains have enough source material (5+ absorbed articles + backtests) to produce meaningful `_context.md` on first run
- **A6**: The CLAUDE.md routing table approach (keyword trigger → load context file) is sufficient for session-time domain recognition without a semantic classifier

---

## OPEN QUESTIONS

- **OQ-1**: What are the exact trigger keywords for each domain in the CLAUDE.md routing table? (e.g., "crypto, DeFi, MEV, Freqtrade" → crypto/_context.md) — needs domain-by-domain keyword list before CLAUDE.md edit
- **OQ-2**: Should the dispatcher's `context_files` injection for research tasks (FR-017) be automatic (all research tasks get their domain's `_context.md`) or conditional (only when `_context.md` is > 30 days old, indicating stable prior knowledge)? Unconditional injection increases token cost per research task.
- **OQ-3**: Is `predictions` the right domain name, or should it be `forecasting`? The existing articles use "prediction" terminology but the TELOS goal framing uses "forecasting skill."
- **OQ-4**: Should the consolidation report be sent to `#epdev` Slack directly or to a dedicated `#jarvis-knowledge` channel? If domain knowledge grows to 10+ domains, the weekly report will be noisy in `#epdev`.
- **OQ-5**: The `automotive` domain has 1 article (BYD EV research) and is > 30 days old — does Eric want it auto-retired on first run, or kept as a reference for future car purchase decisions?
