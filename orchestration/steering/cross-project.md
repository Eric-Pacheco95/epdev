# Cross-Project & Integrations — Steering Rules

> Behavioral constraints for working across repos (epdev, crypto-bot, jarvis-app) and external integrations.
> Load when context involves editing files outside epdev or working with cross-repo dependencies.

## Cross-Repo Operations

- crypto-bot: always read `crypto_alpha_trading_bot.plan.md` first; never suggest switching RUN_MODE to production without Eric's explicit approval
- **Before editing any file outside epdev, run `git status --short` in the target repo; if tree is non-empty OR HEAD is not on default branch, do NOT Edit — propose a backlog row, worktree-off-main patch, or handoff note.** The session-start "N Claude sessions detected" warning is a pre-edit gate for cross-repo work, not ambient noise. Why: 2026-04-08 edit to `crypto-bot/dashboard/app.py` would have been bundled into a concurrent session's PR on `fix/paper-exit-price-resolver`.
- **When entering a non-epdev repo after any gap, verify before assuming:** (1) `git remote show origin | grep 'HEAD branch'` (crypto-bot is `master` not `main`), (2) check README for canonical launcher (crypto-bot: `launch_paper_validation.py` not `start_bot.bat`), (3) `git check-ignore <path>` before staging. Why: 2026-04-08 four same-day frictions each cost 2-5 tool calls.
- Remote Triggers (cloud scheduled tasks) run in fresh-clone isolation: no local file access, no hook firing, no `/skill` invocation, no CLAUDE.md auto-load — only cloud-side connectors. Use local Task Scheduler with `claude -p` for any Jarvis-context work. Slack channels (`#jarvis-inbox`, `#jarvis-voice`) are stateless.

## Loaded by

- Load explicitly when context involves cross-repo edits, crypto-bot work, or Remote Trigger configuration
- `/update-steering-rules --audit` Step A cross-file consistency check reads this file
