# Autonomous Systems — Steering Rules

> Behavioral constraints for autonomous producers, dispatchers, and overnight workers. Loaded on-demand when building, debugging, or configuring autonomous infrastructure. Not loaded during interactive sessions unless relevant.
>
> Extracted from CLAUDE.md to reduce base context pressure (these rules apply in ~5% of sessions).

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

- Any execution gate with both "safely skippable" and "dangerous/rejected" outcomes must use three explicit states — never collapse to binary pass/fail; use `executable` (run it), `manual_required` (safe skip, route to human checklist), `blocked` (security rejection)
- When adding any new data source to autonomous worker prompt assembly: (1) sanitize content before injection (cap length, strip injection patterns + override verbs), (2) validate content at load time against INJECTION_SUBSTRINGS and security contradictions, (3) write-protect the source file in `validate_tool_use.py` for autonomous sessions, (4) gate auto-generated content through a staging file requiring human review before promotion to active
