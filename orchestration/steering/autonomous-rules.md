# Autonomous Systems — Steering Rules

> Behavioral constraints for autonomous producers, dispatchers, and overnight workers.
> Auto-injected by dispatcher into every dispatched task via STEERING_ALWAYS_INJECT.
> Not loaded during interactive sessions unless explicitly added to context_files.

## Architecture

- Autonomous capabilities must follow the three-layer pattern: SENSE (read-only monitoring), DECIDE (dispatcher logic), ACT (worker execution in isolated worktrees) — never combine sensing and acting in the same component
- Any scheduled or background process that mutates git state must operate in a git worktree, never in the main working tree — worktrees with self-healing cleanup (auto-prune stale worktrees on next run) eliminate dirty-tree bugs entirely

## Producer Behavior

- "Idle Is Success" applies to producer OUTPUT (zero proposals/signals when thresholds aren't met = healthy). Silent producer detection applies to producer EXECUTION (zero runs for 2+ consecutive days with no error = suspect) — send Slack alert to `#jarvis-decisions` and suspend until Eric reviews
- Heartbeat auto-signals must require non-zero delta and meet min_delta thresholds — cumulative counters (failure_count, security_event_count) need delta >= 3 to avoid noise from single-count increments; use `min_delta` field in heartbeat_config.json
- Every verification/audit layer must emit its own health signal — if the verifier itself fails to execute, it must produce a louder alert than a verification failure; silent verifier failures create false confidence
- Synthesis threshold is set to 35 (hard ceiling) with tiers at 15/48h and 10/72h — lower ceiling to 15 when velocity drops below 3/day
- After any autonomous /absorb run (Slack poller Tier 1), verify the output chain: signal file exists, TELOS update is appropriate, audit trail is complete

## Agent Definitions

- Agent definitions use Six-Section anatomy (Identity, Mission, Critical Rules, Deliverables, Workflow, Success Metrics) — validate with `python tools/scripts/validate_agents.py`; after production failures, promote the pattern to that agent's Critical Rules as "Never X because Y"

## Model Routing

- Model routing is about correctness, not cost — Opus for judgment/security/architecture, Sonnet for code generation/bulk work, Haiku for extraction/formatting; dispatcher resolves from task `model` field → tier defaults → Opus fallback
- External models (Codex, Gemini) are review-only — never execute, write code, or modify state; route security reviews through Codex adversarial mode; track catch rate per model — if zero catches over 20+ tasks, re-evaluate routing
- Never use the same model to both generate and evaluate its own output — route evaluation to a fresh Sonnet subagent (interactive) or Codex adversarial mode (overnight); track catch rate in history/decisions/

## Security Gates

- Any execution gate with both "safely skippable" and "dangerous/rejected" outcomes must use three explicit states — never collapse to binary pass/fail; use `executable` (run it), `deferred` (pause worker, queue for human review, resume via `claude -p --resume`), `blocked` (security rejection). The `deferred` state replaces the soft `manual_required` convention using Claude Code v2.1.89's native PreToolUse `{"decision": "defer"}` permission. PreToolUse hooks return `"defer"` for high-risk-but-reversible operations (TELOS writes, git push, sensitive path edits); `"block"` remains for irreversible/dangerous patterns (fork bombs, rm -rf, path traversal). Deferred tasks surface in morning briefing with approve/reject; approved tasks resume with full context via `--resume <session_id>`
- When adding any new data source to autonomous worker prompt assembly: (1) sanitize content before injection (cap length, strip injection patterns + override verbs), (2) validate content at load time against INJECTION_SUBSTRINGS and security contradictions, (3) write-protect the source file in `validate_tool_use.py` for autonomous sessions, (4) gate auto-generated content through a staging file requiring human review before promotion to active

## Autonomous Pipeline Rules

- When designing human review for autonomous pipelines, place the approval gate at the batch summary output — not at each intermediate step; auto-approve intermediate artifacts and present a single review surface with smart defaults Eric can override (reduces decision fatigue; per-item gates create backlog that blocks the pipeline)
- **Silent failures require a detector for the failure CLASS before relaunch, and every anti-criterion ISC must exit nonzero on the forbidden state.** Never use `grep -v` / `awk` filter-and-print as the sole verifier — they exit 0 whenever the file is readable, making the anti-criterion a no-op. Prefer a `tools/scripts/verify_*.py` that owns threshold logic and exits 1. How to apply: during `/create-prd` ISC drafting and `/quality-gate` review, every "anti-" criterion must answer "what command exits nonzero on the forbidden state?" — if the answer is "none, just filters output," reject.
- **Pipelines writing to gitignored directories must include a retention ISC: "output file count is monotonically non-decreasing after pipeline runs."** Gitignored dirs have no `git status` visibility; silent empty returns from missing subdirectories mask data loss for weeks. Test the full cycle (write -> consume -> verify survival), not just individual step execution. Why: 2026-04-10 — two independent data-loss bugs discovered in 24h: (1) learning pipeline destroyed 200+ sessions of output via move-to-processed + cleanup, (2) TELOS runner read from nonexistent `processed/` subdir, receiving 0 of 20+ available signals. Both were invisible until manual investigation.
- **Dispatcher ISC criteria must never reference gitignored runtime state (e.g. `data/jarvis_index.db`, running services, live network).** Worktrees are ephemeral clones — gitignored files are absent, so any verify script that reads them silently passes with empty data. How to apply: during ISC authoring for autonomous tasks, run `git check-ignore <verify-script-dependencies>` and reject any criterion whose verify path is gitignored. Also ban bare `find`/`ls` as ISC verifiers — they exit 0 with empty output when no files match; use `test -n "$(find ...)"` or `Exist:` instead.

## Signal Producers

- Prediction signals (backtest, resolution, calibration) use their own synthesis cycle, not /synthesize-signals. Bulk batches (20+) must carry a domain category tag. `suspect_leakage: true` signals require Eric's review before contributing to calibration at full weight.
- An autonomous producer is not "live" until it has produced outcome artifacts, not just run successfully — track what the producer creates (knowledge articles, scored predictions, merged branches), not whether the script exited 0; before updating TELOS or tasklist status, verify at least 1 outcome artifact exists in the last 7 days
- Alerting collectors that report shared-host metrics (TCP connections, memory, file handles) must attribute to specific processes by name+cmd, never blanket-blame a class like "Claude". How to apply: any new collector emitting alert text must call a top-N-holder helper (`tools/scripts/lib/net_util.py` for TCP); reject generic "close X sessions" templates in favor of named-process attribution

## Cleanup & Retention

- **Never call `git worktree remove --force` directly — use `_safe_worktree_remove()` from `tools/scripts/lib/worktree.py`.** The `memory/learning/synthesis/` directory must be excluded from ALL pipeline cleanup, rotation, and move-to-processed logic. Why: git's internal rm-rf follows Windows junctions and destroyed 367 signals across 4 days; the same class of cleanup bug independently destroyed a synthesis doc. How to apply: any overnight or dispatcher cleanup step that prunes worktrees or rotates output directories must call `_safe_worktree_remove()` and explicitly exclude `memory/learning/synthesis/` from its scope.

## Loaded by

- `tools/scripts/jarvis_dispatcher.py` — STEERING_ALWAYS_INJECT (every dispatched task)
- `heartbeat_config.json` — context_files entry
- `.claude/skills/synthesize-signals/SKILL.md` — Step 0.5 (producer behavior + synthesis thresholds)
- `.claude/skills/learning-capture/SKILL.md` — Step 0.5 (producer behavior + signal constraints)
- `.claude/skills/create-prd/SKILL.md` — Step 0.9 (anti-criterion verification constraints)
- `.claude/skills/quality-gate/SKILL.md` — Step 0 (anti-criterion exit-code rules)
