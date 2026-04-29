# Autonomous Systems — Steering Rules

> Behavioral constraints for autonomous producers, dispatchers, and overnight workers.
> Auto-injected by dispatcher into every dispatched task via STEERING_ALWAYS_INJECT.
> Not loaded during interactive sessions unless explicitly added to context_files.

## Architecture

- Autonomous capabilities must follow the three-layer pattern: SENSE (read-only monitoring), DECIDE (dispatcher logic), ACT (worker execution in isolated worktrees) — never combine sensing and acting in the same component
- **Dispatcher monitoring must use single authority per resource.** When two monitoring systems both cover the same producers (e.g. `producer_recency` via producers.json + `producer_health` via DB), the one with the allowlist and canonical source is authoritative; the other must be demoted to informational-only and removed from the remediation map. When both fire simultaneously and dedup logic depends on one being OK, genuine failures trigger a close-reopen task loop instead of resolution. How to apply: `producer_recency` (producers.json + file mtimes) is the canonical health check; `producer_health` (DB query) is read-only context. Why: dual-authority produces infinite remediation loops on real failures — exactly when correct behavior matters most.
- **Documentation-only governance rules collapse to the system default in multi-author systems.** Before calling a behavioral rule "adopted," confirm it has at least one of: (a) PreToolUse/PostToolUse hook enforcement, (b) lint/CI gate, or (c) a fail-safe default where forgetting costs something observable. A rule with no enforcement mechanism is a note. Why: 2/47 skills had explicit `model:` pins before Alt B — five months of steering rules didn't override the harness default.
- **When changing a function's return type from `bool` to `Optional[int]`, audit ALL callers for truthiness guards (`if not x:`, `if x:`) and replace with `is None` / `is not None` before shipping.** `Enforced by: [ADVISORY]` Slot 0 is falsy — a caller checking `if not slot:` silently bypasses the guard on every normal single-slot run where `slot == 0`. How to apply: after any return-type change from bool → Optional[int], run `grep -n "if not <varname>\|if <varname>:"` across all callers before merging. Why: commit `dc3fe71` changed `_dispatch_one`'s slot return type; `_dispatcher_slot = 0` on a 1-slot config caused the `if not _dispatcher_slot:` guard to behave as if slot acquisition had failed, making the dispatcher crash on every task. Evidence: `memory/learning/failures/2026-04-26_falsy-slot-zero-optional-int-trap.md` (rating 8).

> **Producer lifecycle, signal/alert design, and process/lock/worktree primitives** moved 2026-04-27 to keep this file under cap. See `orchestration/steering/producer-signal-design.md` and `orchestration/steering/process-lock-safety.md` — both auto-injected via STEERING_ALWAYS_INJECT alongside this file.

## Agent Definitions

- Agent definitions use Six-Section anatomy (Identity, Mission, Critical Rules, Deliverables, Workflow, Success Metrics) — validate with `python tools/scripts/validate_agents.py`; after production failures, promote the pattern to that agent's Critical Rules as "Never X because Y"

## Model Routing

- Model routing is about correctness, not cost — Opus for judgment/security/architecture, Sonnet for code generation/bulk work, Haiku for extraction/formatting; dispatcher resolves from task `model` field → tier defaults → Opus fallback
- External models (Codex, Gemini) are review-only — never execute, write code, or modify state; route security reviews through Codex adversarial mode; track catch rate per model — if zero catches over 20+ tasks, re-evaluate routing
- Never use the same model to both generate and evaluate its own output — route evaluation to a fresh Sonnet subagent (interactive) or Codex adversarial mode (overnight); track catch rate in `data/review_gate_log.jsonl` (one JSONL entry per eval run: `date`, `task_slug`, `findings_count`, `applied_fix`, `rate_limited`; summarize to `history/decisions/` at quarterly audit)
- `[MODEL-DEP]` Capability-gap pairing (re-validate quarterly; last validated 2026-04-16): Opus judges Sonnet output, Sonnet judges Haiku output — evaluator must be strictly stronger than generator; if the gap closes (evaluator catch rate <10% over 20+ samples), disable the eval loop and alert rather than continuing to spend with zero quality delta. Current status: gap confirmed (Opus 4.7 > Sonnet 4.6 > Haiku 4.5); 1 positive catch-rate data point logged (2026-04-04, 3 High findings); systematic 20-sample tracking not yet established — log each eval outcome to `history/decisions/` with `catch_result:` field

## Task Typing (S×A + S×V)

PRD frontmatter must declare four axes — each `low | medium | high`:

```yaml
---
stakes:        low | medium | high
ambiguity:     low | medium | high
solvability:   low | medium | high
verifiability: low | medium | high
---
```

**Stakes** is shared between S×A and S×V — declared once, consulted in both phases.

**GENERATE-phase routing** (consumed by `/implement-prd` before BUILD):

| Axis | Drives |
|------|--------|
| `stakes` | Generator tier (low=Haiku, medium=Sonnet, high=Opus) |
| `ambiguity` | Pre-code effort — research / first-principles / spec clarification BEFORE writing code |
| `solvability` | Attempt-vs-escalate and retry depth — `low` = escalate model tier or route to human; `medium` = chunk + budget 2-3 retries; `high` = attempt directly |

**EVAL-phase routing** (consumed by `/implement-prd` REVIEW GATE Step 2):

| Axis | Drives |
|------|--------|
| `verifiability` | Evaluator tier — `high` = script-oracle (skip Sonnet subagent); `medium` = Sonnet subagent + detector; `low` = Opus subagent OR `/second-opinion` OR Codex adversarial OR HITL |
| `stakes` | Eval depth multiplier — `stakes: high` forces HITL regardless of V |
| `solvability` | Danger-cell signal — `solvability: low` × `verifiability: low` forces HITL (fluent-bluff guard) |

**Effort scaling is differentiated across the three effort axes, not duplicated:**
- `ambiguity` scales effort **before** code (more research, spec clarification)
- `solvability` scales effort **during** code (retries, model escalation, chunking)
- `verifiability` scales effort **after** code (evaluator depth, HITL, adversarial)

Definitions for `stakes` and `ambiguity` are authoritative in `memory/knowledge/harness/subagent_model_routing.md` (S×A rubric). Definitions for `solvability` and `verifiability` are authoritative in `orchestration/steering/solvability-spectrum.md` and `orchestration/steering/verifiability-spectrum.md`.

**Terminology guard:** Use **"escalate"** (not `defer`) for the Solvability `low` action. `defer` is reserved for the PreToolUse permission state in `security/validators/validate_tool_use.py` (see Security Gates below).

## Security Gates

- Any execution gate with both "safely skippable" and "dangerous/rejected" outcomes must use three explicit states — never collapse to binary pass/fail; use `executable` (run it), `deferred` (pause worker, queue for human review, resume via `claude -p --resume`), `blocked` (security rejection). The `deferred` state replaces the soft `manual_required` convention using Claude Code v2.1.89's native PreToolUse `{"decision": "defer"}` permission. PreToolUse hooks return `"defer"` for high-risk-but-reversible operations (TELOS writes, git push, sensitive path edits); `"block"` remains for irreversible/dangerous patterns (fork bombs, rm -rf, path traversal). Deferred tasks surface in morning briefing with approve/reject; approved tasks resume with full context via `--resume <session_id>`
- When adding any new data source to autonomous worker prompt assembly: (1) sanitize content before injection (cap length, strip injection patterns + override verbs), (2) validate content at load time against INJECTION_SUBSTRINGS and security contradictions, (3) write-protect the source file in `validate_tool_use.py` for autonomous sessions, (4) gate auto-generated content through a staging file requiring human review before promotion to active
- **Any autonomous task or harness that may invoke `gh`, `bq`, `gcloud`, `aws`, `kubectl`, or `docker` must have a PreToolUse hook with an explicit resource allowlist before shipping — worktree CWD isolation does NOT constrain OAuth scope; `gh pr create --repo other-repo` executes successfully from any worktree.** Why: worktree-as-permission-boundary is a false assumption; OAuth credentials are user-scoped, not directory-scoped.
- **`tools/scripts/` must be included in the autonomous-session write-protection list in `validate_tool_use.py`.** Any new script added to `tools/scripts/` for autonomous use must also be registered in an explicit allowlist checked before Bash execution in autonomous mode. Write-protection is first; allowlist is second. Why: voice-pipeline and Notion-inbox work pulls external content into autonomous prompts; without write-protection on `tools/scripts/`, a prompt injection could write + execute arbitrary Python under the autonomous agent's authority. Red-team surfaced as HIGH (2026-04-19); unrelated to any migration proposal — standing gap.

## Autonomous Pipeline Rules

- **When overnight quality gate FAIL includes a `file:line` target, treat it as an executable test-addition task: read the range, write tests targeting it, verify exit 0, merge.** Skip the investigation phase — the file:line pair is the investigation output.
- When designing human review for autonomous pipelines, place the approval gate at the batch summary output — not at each intermediate step; auto-approve intermediate artifacts and present a single review surface with smart defaults Eric can override (reduces decision fatigue; per-item gates create backlog that blocks the pipeline)
- **Silent failures require a detector for the failure CLASS before relaunch, and every anti-criterion ISC must exit nonzero on the forbidden state.** Never use `grep -v` / `awk` filter-and-print as the sole verifier — they exit 0 whenever the file is readable, making the anti-criterion a no-op. Prefer a `tools/scripts/verify_*.py` that owns threshold logic and exits 1. How to apply: during `/create-prd` ISC drafting and `/quality-gate` review, every "anti-" criterion must answer "what command exits nonzero on the forbidden state?" — if the answer is "none, just filters output," reject.
- **Pipelines writing to gitignored directories must include a retention ISC: "output file count is monotonically non-decreasing after pipeline runs."** Gitignored dirs have no `git status` visibility; silent empty returns from missing subdirectories mask data loss for weeks. Test the full cycle (write -> consume -> verify survival), not just individual step execution. Why: 2026-04-10 — two independent data-loss bugs discovered in 24h: (1) learning pipeline destroyed 200+ sessions of output via move-to-processed + cleanup, (2) TELOS runner read from nonexistent `processed/` subdir, receiving 0 of 20+ available signals. Both were invisible until manual investigation.
- **Dispatcher ISC criteria must never reference gitignored runtime state (e.g. `data/jarvis_index.db`, running services, live network).** Worktrees are ephemeral clones — gitignored files are absent, so any verify script that reads them silently passes with empty data. How to apply: during ISC authoring for autonomous tasks, run `git check-ignore <verify-script-dependencies>` and reject any criterion whose verify path is gitignored. Also ban bare `find`/`ls` as ISC verifiers — they exit 0 with empty output when no files match; use `test -n "$(find ...)"` or `Exist:` instead.

## Loaded by

- `tools/scripts/jarvis_dispatcher.py` — STEERING_ALWAYS_INJECT (every dispatched task)
- `heartbeat_config.json` — context_files entry
- `.claude/skills/create-prd/SKILL.md` — Step 0.9 (anti-criterion verification constraints + Task Typing four-axis frontmatter)
- `.claude/skills/implement-prd/SKILL.md` — Step 1 (Task Typing label extraction + REVIEW GATE evaluator routing by verifiability)
- `.claude/skills/quality-gate/SKILL.md` — Step 0 (anti-criterion exit-code rules + Task Typing frontmatter check)

## Sister files (auto-injected together)

- `orchestration/steering/producer-signal-design.md` — producer lifecycle, alert/signal design
- `orchestration/steering/process-lock-safety.md` — worktree, lock, subprocess primitives
