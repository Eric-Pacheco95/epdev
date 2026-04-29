---
name: second-opinion
description: Generate a self-contained external-reviewer prompt for independent repo audit
---

# IDENTITY and PURPOSE

Generate a self-contained harness-first review prompt for an external agent (Codex, GPT, Gemini, human). This skill produces the brief — not the audit. Every wall becomes a stub/mock/fake task. "Could not verify" is not an acceptable outcome.

# DISCOVERY

## One-liner
Generate a self-contained external-reviewer prompt for independent repo audit

## Stage
PLAN

## Syntax
/second-opinion [--static | --dynamic] [--target <path-or-url>] [--out <path>] [--reviewer <name>]

## Parameters
- `--static` — read-only variant (no execution, no harnesses, ~1 hour budget)
- `--dynamic` — full harness + runtime checks variant (default, 4+ hour budget)
- `--target <path-or-url>` — repo to review (default: current working repo)
- `--out <path>` — output prompt file (default: `./REVIEW_PROMPT.md`)
- `--reviewer <name>` — reviewer identifier woven into intro (default: `Codex`)

## Examples
- `/second-opinion` — full dynamic Codex prompt for current repo at ./REVIEW_PROMPT.md
- `/second-opinion --static` — read-only static-scan variant
- `/second-opinion --reviewer "GPT-5" --out prompts/gpt5_review.md`
- `/second-opinion --target https://github.com/user/otherrepo --dynamic`

## Chains
- Before: Eric wants independent perspective on a codebase
- After: Eric pastes the file into the external agent; on return, optionally `/learning-capture` the findings
- Composes: pairs with `/deep-audit` (internal Jarvis audit) as the external counterpart
- Full: /second-opinion > [human: paste output into external model] > /learning-capture

## Output Contract
- Input: flags + target
- Output: single markdown file at `--out` path, self-contained, ready to paste
- Side effects: one file written; no code changes

## autonomous_safe
true

# STEPS

## Step 0: INPUT VALIDATION

- Unknown flags (not `--target`, `--out`, `--reviewer`, `--dynamic`, `--static`): print usage, STOP
- Both `--dynamic` and `--static`: "Conflicting flags: mutually exclusive", STOP
- Default mode: `--dynamic` unless `--static` specified

1. Resolve: `--target` (default: `git rev-parse --show-toplevel`), `--out` (default: `./REVIEW_PROMPT.md`), `--reviewer` (default: `Codex`), mode. If subagent: `model="claude-sonnet-4-6"` (see subagent_model_routing.md).
2. Read the embedded TEMPLATE block matching mode.
3. Substitute `{REVIEWER}`, `{TARGET}`, `{DATE}` (YYYY-MM-DD), `{REPO_HINT}`.
4. Write to `--out` (create parent dirs if needed); print the OUTPUT FORMAT block.

# OUTPUT FORMAT

Chat response after writing the file:

```
Wrote: <out_path>
Mode: <static|dynamic> | Reviewer: <name> | Target: <repo>

Paste the contents of <out_path> into your <reviewer> session and run it.

Blind spots the reviewer will have (set expectations):
- Windows-specific code paths (only statically verifiable / simulated)
- Real MCP servers, Task Scheduler, iCloud integration
- Real API behavior for Anthropic/Slack/Tavily/etc
- Anything in gitignored personal dirs (memory/, history/, data/)
```

# INPUT

INPUT:

# VERIFY

- Output file exists at `--out` path and is non-empty | Verify: `ls --out` exits 0 and file size > 0
- All template placeholders ({REVIEWER}, {TARGET}, {DATE}, {REPO_HINT}) are substituted | Verify: `grep '{' <output-file>` returns zero hits inside the prompt body
- Output file is NOT written inside a gitignored path (unless explicitly requested) | Verify: `git check-ignore <--out path>` returns no match
- Mode section matches flag: dynamic → contains 'Phase 3 — Dynamic' and H1-H8 playbook; static → does NOT contain those strings | Verify: `grep 'Phase 3' <output>` for dynamic; absence for static
- Output file opens with reviewer identification line (not blank/empty header) | Verify: `head -3 <output>` begins with "You are doing"

# LEARN

- No auto-signal — prompt-generation utility, not an audit.
- External reviewer findings → `/learning-capture` (rate by severity); consistent Jarvis blind-spots → blind-spot signal.
- If the external reviewer’s top findings are never addressed (not in commits 30+ days after), the review cadence is too frequent — drop to quarterly and tag results as research-only.
- Track harness reuse rate: if H1–H8 harnesses built in one run are never reused, the --dynamic prompt over-invests in scaffolding; consider recommending --static for that reviewer context.
- If the same reviewer (Codex/GPT/etc.) consistently misses the same blind-spot class (e.g., Windows paths), update the `## Ground rules` section to call it out explicitly.

---

# TEMPLATE: DYNAMIC

```markdown
You are doing an independent deep audit of "{REPO_HINT}" (target: `{TARGET}`). Solo author, built with Claude Code over several months. I want a harsh second opinion with runtime evidence, not static skimming. You have a 4+ hour budget and sufficient cloud compute. Depth over speed.

## Prime directive

**There are no walls. Every blocker becomes a harness task.** If a script needs a secret, stub it. If it needs the `claude` CLI, write a fake `claude` shim on PATH that returns fixtures. If it needs an MCP server, spawn a stdio mock. If it needs Windows, monkey-patch the stdlib. If it needs a directory that isn't in the repo, fabricate the directory from schema inferred by reading the writer. If a dep is missing from `requirements.txt`, install it from the import statements. If something can't be executed directly, simulate it. "Could not verify" is not an acceptable outcome — every finding must have runtime evidence or a documented reason the harness itself is the problem.

Budget up to 45 minutes per blocker on harness construction before you downgrade a check to static-only. Log every harness you build in the final report so it can be reused.

## Execution authorization

ALLOWED:
- Clone, checkout scratch branches (no push)
- Create and activate a venv; install any Python package needed (`pip install <anything>`)
- Install system packages via apt if available
- Build fake CLIs, fake MCP servers, fake API endpoints (localhost HTTP, stdio fake, file-based fixtures)
- Monkey-patch stdlib (`time.time`, `os.name`, `sys.platform`, `pathlib`, `subprocess`) to simulate Windows, slow clocks, failure modes
- Write freely inside `_codex_scratch/` (create it, gitignore it, never commit it)
- Fabricate synthetic `memory/`, `history/`, `data/` trees — infer schema from writer code, populate with realistic dummy data
- Create a synthetic `.env` with fake values for every variable referenced in code
- Run any script under `tools/scripts/`, `tests/`, `security/validators/`, `orchestration/`
- Run every test suite you find
- Use `vulture`, `ruff`, `pyflakes`, `mypy`, `bandit`, `pip-audit`, `semgrep` — install whichever help

FORBIDDEN:
- Modify any tracked file in the working tree (scratch dir is fine)
- `git push`, `git commit`, touching any remote
- Calls to real external services with real credentials (Anthropic, OpenAI, Slack, Tavily, Firecrawl, GitHub API writes, email). Use fakes.
- Writing to the real `memory/`, `history/`, `data/` — redirect via env vars or monkey-patching

## Harness construction playbook (build BEFORE dynamic checks)

**H1 — Fake `claude` CLI.** Create `_codex_scratch/bin/claude` (chmod +x), prepend to PATH. Accept `-p`, `--resume`, `--output-format`, any flag the repo uses. Read fixtures from `_codex_scratch/claude_fixtures/`. Return JSON matching Claude Code's stream-json format. Env-flag modes: success, rate-limit (stdout contains "hit your limit", exit 0), network error, malformed output, empty. Log every call to `_codex_scratch/claude_calls.jsonl`.

**H2 — Synthetic `.env`.** Grep every `os.environ`/`os.getenv`/`dotenv` lookup. Build `_codex_scratch/.env` with obviously-fake values (`sk-FAKE-...`, `xoxb-FAKE-...`) for each.

**H3 — Fake MCP servers.** For each MCP server in `.claude/settings.json` / `.mcp.json`: write a minimal stdio fake that speaks MCP JSON-RPC, lists advertised tools, returns canned responses.

**H4 — Fake HTTP sinks.** Stand up local FastAPI / `http.server` on `127.0.0.1:<port>` matching endpoints for Slack/Anthropic/OpenAI/Tavily/Firecrawl/GitHub. Redirect via env base URLs. Log to `_codex_scratch/http_calls.jsonl`.

**H5 — Synthetic data trees.** Read every writer. For every path under `memory/`/`history/`/`data/`: infer schema, create at `_codex_scratch/fake_<name>/`, populate with 10-50 realistic synthetic records. Redirect reads via monkey-patch or env.

**H6 — Windows simulator.** `_codex_scratch/windows_shim.py` that monkey-patches: `time.time` to 15ms granularity; `sys.platform='win32'`; `os.name='nt'`; `sys.stdout.encoding='cp1252'`. Run target scripts via this shim.

**H7 — Hook invoker.** `_codex_scratch/invoke_hook.py` — takes hook name + synthetic tool_use payload, looks up matcher in `settings.json`, runs the hook with correct env/stdin, reports exit + stdout + side effects.

**H8 — Dependency resolver.** AST-scan all `.py` imports, diff against `requirements*.txt` + stdlib, pip-install the gap until clean.

## Phase 1 — Orientation (~20 min)

1. `CLAUDE.md` at repo root — identity, ALGORITHM loop, ISC quality gate, steering rules. Every rule was written after a real incident; treat as invariants the codebase SHOULD uphold.
2. `memory/work/TELOS.md` — skim mission only.
3. `orchestration/tasklist.md`, `orchestration/README.md`.
4. `ls .claude/skills/` — verify any count claimed in CLAUDE.md.
5. `.claude/settings.json`, `.mcp.json` if present.
6. `security/constitutional-rules.md`, `ls security/validators/`.
7. `git log --oneline -100`, `git shortlog -sn`, `git log --stat -30`.
8. Map entry points: heartbeat, overnight runner, dispatcher, routines engine, backlog append.

## Phase 2 — Harness build (~30-45 min)

Execute H1-H8. End state: `_codex_scratch/` can run any script without hitting a real external service.

## Phase 3 — Static scan (~45 min)

Draft findings in these buckets. Phase 4 will confirm with runtime evidence.

**A. Doc/reality drift** — claimed skills/paths/tasks that don't match reality; stale counts/dates; claimed "complete" producers not actually wired.

**B. Steering rule violations** (highest signal — paid-for lessons):
- Anti-criterion no-ops (grep -v / awk filter-and-print verifiers that exit 0 on violation)
- `time.time()` uniqueness assumptions (Windows 15ms tick)
- Orphaned file copies after relocation (multi-reader paths diverging)
- `claude -p` exit-0 consumers not checking for rate-limit strings
- MCP wildcard allow-lists on servers with mutation tools
- Hook matchers not covering their validators
- Non-ASCII in Python print paths (cp1252 hazard)
- Parallel test suites duplicating instead of extending
- Blanket-blame alert text in collectors (generic "Claude" vs named-process)
- `git add -f`, `--no-verify`, bypassed gitignore
- `subprocess(..., shell=True)` with interpolation
- Naive `datetime.now()` for durable timestamps

**C. Security** — `git ls-files memory/ history/` (should be empty); secret grep; validator TOCTOU/traversal/injection; path guards that can be bypassed.

**D. Dead code** — scripts/skills with zero inbound references, routines targets that don't exist, old TODOs.

**E. Architectural smells** — skill/module cycles, god-files >800 lines, duplicated JSONL logic, uncategorized signals, unlocked read-modify-write on shared files.

**F. Correctness** — bare excepts, swallowed exceptions, schema drift writer/reader pairs, off-by-ones, unchecked None.

## Phase 4 — Dynamic checks (~2.5+ hours, the core)

**4.1 Run every test suite.** `pytest -xvs tests/` + each script's `__main__` self-test. Record pass/fail/error/flaky. Root-cause every failure in 1-2 sentences.

**4.2 Validator fuzzing.** Every script in `security/validators/`: 30+ adversarial inputs (path traversal, shell metachars, null bytes, unicode homoglyphs, JSON bombs, symlinks, oversized, empty, malformed). Use H7 to verify hook matchers actually route each validator.

**4.3 Anti-criterion verifier audit.** Every `tools/scripts/verify_*.py` and every `Verify:` command in PRDs/CLAUDE.md/skills: construct synthetic forbidden-state input, run verifier, **assert exit != 0**. Exit 0 on forbidden state = CRITICAL.

**4.4 Windows-clock simulation.** Using H6: run backlog-append (and any other id-generator) 2000× rapid succession. Count collisions. Repeat with two parallel processes.

**4.5 Routines engine full dry-run.** Every entry in `orchestration/routines.json`. Fake externals via H1/H3/H4/H5. Per-routine: exit, logs, files touched. Flag interval/skill mismatches, missing targets.

**4.6 Dispatcher + backlog round-trip.** Append synthetic task, run dispatcher, verify pickup → processed (via fake claude) → terminal state. File-lock correctness: two parallel appenders × 500 iterations each, assert zero lost writes.

**4.7 Concurrent-write stress.** Every shared JSON/JSONL with >1 writer: 4 writers × 500 iterations parallel. Assert no corruption / lost updates / interleaved records.

**4.8 Hook simulation.** Every hook in `settings.json`: synthetic matching tool call via H7, verify exit + stdout + side effects.

**4.9 Import graph + dead code.** Full graph across `tools/scripts/`, `.claude/skills/`, `orchestration/`. Run `vulture`. Report unreachable modules/functions and cycles.

**4.10 Schema drift.** Every JSON/JSONL with writer A + reader B: diff A's write keys vs B's expected keys. Report mismatches.

**4.11 Static analyzers.** `ruff`, `pyflakes`, `mypy --ignore-missing-imports`, `bandit -r .`, `semgrep --config=auto .`. Top 20 by severity from each.

**4.12 Git hygiene.** `git fsck`, blobs >1MB in history, merged-undeleted branches, stale worktrees, `git ls-files` sanity on personal dirs.

**4.13 Rate-limit handling.** H1 in rate-limit mode. Every `claude -p` consumer: verify it detects + handles. Treating as success = HIGH finding.

**4.14 Signal/synthesis pipeline end-to-end.** Drop 50 synthetic signals into H5 fake memory, run synthesis routine, verify output shape, run `verify_synthesis_recall.py` against a truncated/fabricated synthesis and assert it exits nonzero.

## Phase 5 — Report (~30 min)

Write to `_codex_scratch/REVIEW.md`:

```
# {REVIEWER} Deep Audit — {REPO_HINT}
Date: {DATE} | HEAD: <sha> | Wall time: <hh:mm>
Tests ran/passed/failed/errored: <counts>
Harnesses built: <count>

## TL;DR
<5 bullets, severity-ranked>

## Findings

### CRITICAL
- **<title>** — `path:line`
  Static: <snippet>
  Dynamic evidence: <command + output>
  Impact: <1-2 sentences>
  Fix: <concrete>

### HIGH / MEDIUM / LOW
...

## Dynamic check results
<table per 4.1-4.14>

## What's GOOD
<3-5 bullets — prevents over-refactor>

## Meta-observations
<recurring bug classes, architectural patterns causing pain>

## Harnesses built (reusable)
<list each: path + invocation>

## Command log
<full reproducible log>

## STATIC-ONLY findings
<with reason the harness itself failed — should be near-empty>
```

## Ground rules

- **Harnesses, not excuses.** Walls are tasks.
- **Every finding needs file:line + runtime evidence** (STATIC-ONLY only with justification).
- **Harsh, no sycophancy.** Flag over-abstraction, speculative helpers, narrating comments; say delete if it should go.
- **CLAUDE.md "AI Steering Rules" + "Core Principles" violations are top-signal.** Surface loudly.
- **Concrete fixes.** "Replace X on line 47 with Y because Z" — never "refactor this".
- **4+ hours expected.** Go deeper on 4.2, 4.6, 4.7, 4.13 if finishing early.

Begin Phase 1 now. Work continuously through Phase 5. One report at the end.
```

---

# TEMPLATE: STATIC

```markdown
You are doing an independent second-opinion review of "{REPO_HINT}" (target: `{TARGET}`). Solo project, built with Claude Code. I want fresh eyes — no prior context. Read-only static analysis, ~1 hour budget.

## Orientation (first, in order)

1. `CLAUDE.md` at the repo root — identity, ALGORITHM loop, ISC quality gate, steering rules. Every rule was added after a real incident; treat as invariants.
2. `memory/work/TELOS.md` — skim mission only.
3. `orchestration/tasklist.md` and `orchestration/README.md`.
4. `ls .claude/skills/` — verify any count claimed in CLAUDE.md.
5. `.claude/settings.json` — hooks, permissions, MCP, validators.
6. `security/constitutional-rules.md`, `ls security/validators/`.
7. `git log --oneline -50` and `git log --stat -20`.

Timebox orientation to ~15 min. Sample, don't exhaustively read.

## Scan buckets

Organize findings below. For each, cite `file:line` and quote the snippet.

### A. Doc/reality drift
- Skills claimed that don't exist; paths referenced in rules that don't exist; `[x]` tasks with no artifact; stale counts/dates.

### B. Steering rule violations (highest signal)
- Anti-criterion no-ops (`grep -v`/`awk` verifiers exiting 0 on violation)
- `time.time()` uniqueness without ns + counter (Windows hazard)
- Orphaned file copies after relocation
- `claude -p` exit-0 consumers not checking rate-limit strings
- MCP wildcard allow-lists on mutation servers
- Hook matchers not covering their validators
- Non-ASCII in Python print paths (cp1252 hazard)
- Parallel test suites instead of extending
- Blanket-blame alert text in collectors

### C. Security
- `git ls-files memory/ history/` (should be empty)
- Secret grep in `.py`/`.json`/`.md`/`.env*`
- Validator TOCTOU, path traversal, shell injection, bypasses
- `subprocess(..., shell=True)` with interpolation
- `git add -f`, `--no-verify`

### D. Dead code
- Scripts with no inbound references; skills not referenced anywhere; routines targets missing; old TODOs (date via blame).

### E. Architectural smells
- Circular deps, god-files >800 lines, duplicated logic, uncategorized signal writers, unlocked read-modify-write.

### F. Correctness
- Bare excepts, naive `datetime.now()`, schema drift, off-by-ones, unchecked None.

## Output format

Single markdown report:

```
# {REVIEWER} Independent Review — {REPO_HINT}
Date: {DATE}
Scope: <sha of HEAD>

## TL;DR
<5 bullets, severity-ranked>

## Findings

### CRITICAL
- **<title>** — `path:line`
  Evidence: `<snippet>`
  Why it matters: <1-2 sentences>
  Fix: <concrete, not hand-wavy>

### HIGH / MEDIUM / LOW
...

## What's GOOD
<3-5 bullets — prevents over-refactor>

## Meta-observations
<patterns across findings>

## Could not verify
<anything that would need execution — list here for a dynamic follow-up pass>
```

## Ground rules

- **Read-only.** No file modifications.
- **Cite evidence.** `file:line` + snippet required. Uncited = ignored.
- **Concrete fixes.** "Refactor this" = useless.
- **Depth > breadth.** 10 real bugs > 50 nits.
- **Harsh, no sycophancy.** Flag over-abstraction and dead code; say delete if it should go. Steering rule + Core Principle violations are highest-signal.

Begin with orientation, then scan, then report.
```
