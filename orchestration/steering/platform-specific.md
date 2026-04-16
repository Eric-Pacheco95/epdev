# Platform-Specific — Steering Rules

> Platform constraints for Windows, Task Scheduler, MCP servers, and Claude Code hooks.
> Load when working on platform-specific tooling, scheduled tasks, or hook configuration.

## Windows & Scheduling

- Python CLI scripts that print to terminal must use ASCII-only output — Windows cp1252 encoding breaks Unicode box-drawing chars with a hard UnicodeEncodeError; when assigning external content (scraped, API, user input) to variables that will be printed/logged, strip non-ASCII at assignment: `raw.encode('ascii', errors='replace').decode('ascii')`
- Always smoke-test scheduled jobs, hook wrappers, and `claude -p` scripts via their actual execution context (Task Scheduler or standalone CMD), never from within an active Claude Code session — subprocess contention causes hangs, and Git Bash is not a valid proxy for Task Scheduler behavior
- **Never derive identity, ordering, or dedup keys from `time.time()` — Windows tick is ~15ms.** Use `time.time_ns()` plus a process-local monotonic counter (`last_id = max(time.time_ns(), last_id + 1)`), or carry a Windows self-test asserting uniqueness across rapid successive calls.
- `[MODEL-DEP]` Any `claude -p` consumer must check stdout for rate limit messages ("hit your limit") before treating exit code 0 as success — rate-limited runs return exit 0 with zero work done
- **All `claude -p` subprocess calls must pass prompts via stdin (`subprocess.run([..., "-p"], input=prompt, capture_output=True, text=True)`), never as a positional CLI arg.** Windows cmd-line length limit (WinError 206) triggers above ~32KB. Flag any `subprocess.run(["claude", "-p", variable, ...])` where the variable is unbounded. Why: domain_knowledge_consolidator.py and jarvis_dispatcher.py independently hit this — two implementations converging confirms it is universal on Windows.
- **All Jarvis scheduled tasks must use `New-ScheduledTaskPrincipal -LogonType S4U -RunLevel Highest`; always pass `-TaskPath` to `Set-ScheduledTask`.** Claude Routines (CronCreate) are session-time behavioral guardrails only — not replacements for overnight scheduled tasks (Routines require active REPL, expire in 7 days). Why: Interactive logon fails with 0x800710E0 when user is logged off; omitting `-TaskPath` causes silent HRESULT failures while printing success.
- **All PowerShell mutation cmdlets (`Set-ScheduledTask`, `Set-*`, `Remove-*`) must: (1) discover `-TaskPath` via `Get-ScheduledTask`, (2) wrap in `try/catch` with `-ErrorAction Stop`, (3) verify with a read-back query on the mutated field.** Never trust `Write-Host` output strings as proof of mutation success — non-terminating errors print success while silently skipping the mutation. Why: 18/20 task logon-type updates silently failed (HRESULT 0x80070002) while printing "Updated: $t".

## MCP & Hooks

- MCP servers: stdio transport (npx/uvx), `.mcp.json` in project root. Two distinct behaviors: **`.mcp.json` config edits require session restart** (structural config change); runtime tool/resource additions propagate via `list_changed` notifications without disconnect. Debug by reading `C:/Users/ericp/.claude.json` directly (`mcp list` shows health only)
- Never use `mcp__<server>__*` wildcards in allow lists for servers with mutation tools — enumerate read tools explicitly; wildcards only safe for read-only servers
- Hook commands must use absolute paths (relative breaks silently); hooks fire on every message — never print content already in CLAUDE.md, only surface dynamic state

## Loaded by

- Load explicitly when context includes scheduled task work, hook edits, or platform-specific tooling
- `.claude/skills/extract-harness/SKILL.md` — Step 0.5 (platform constraints during harness extraction)
- `/update-steering-rules --audit` Step A cross-file consistency check reads this file
