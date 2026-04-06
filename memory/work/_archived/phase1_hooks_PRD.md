# PRD: Phase 1 — Lifecycle Hooks & Defensive Tests

> For implementation in Cursor Pro. Read CLAUDE.md and security/constitutional-rules.md for context.

## Objective

Create the first lifecycle hooks and defensive tests for the epdev Jarvis system.
Runtime: Python 3.12 (available on this Windows machine). No Go/Bun available yet.

## Deliverables

### Hook 1: Session Start (`tools/scripts/hook_session_start.py`)

**Trigger**: Beginning of each Claude Code session
**Actions**:
1. Print a welcome banner with current date/time
2. Load and display active tasks from `orchestration/tasklist.md` (just the unchecked items)
3. Check for unprocessed learning signals in `memory/learning/signals/` (count them)
4. If signals > synthesis_trigger (10), remind to run synthesis
5. Display any recent security events from last 7 days

**Output**: Formatted summary to stdout

### Hook 2: Security Validator (`security/validators/validate_tool_use.py`)

**Trigger**: PreToolUse — before any Bash command executes
**Actions**:
1. Read the proposed command from stdin (JSON: `{"tool": "Bash", "input": {"command": "..."}}}`)
2. Check against blocked patterns from constitutional-rules.md:
   - `rm -rf /`, `rm -rf ~`, `rm -rf *`
   - `git push --force` to main/master
   - Fork bombs
   - Disk format/partition commands
   - Access to protected paths (~/.ssh, ~/.aws, etc.)
3. Check for secret patterns in command output paths
4. Output JSON: `{"decision": "allow"}` or `{"decision": "block", "reason": "..."}`

### Hook 3: Learning Capture (`tools/scripts/hook_learning_capture.py`)

**Trigger**: End of session or manual invocation
**Actions**:
1. Prompt for outcome rating (1-10) — or accept as argument
2. Accept signal description as argument
3. Write signal to `memory/learning/signals/YYYY-MM-DD_{slug}.md` using template from memory/README.md
4. If failure, write to `memory/learning/failures/` with root cause template
5. Update signal count

### Defensive Test 1: Injection Detection (`tests/defensive/test_injection_detection.py`)

**Tests**:
1. Feed the security validator common prompt injection patterns and verify they're blocked
2. Test path traversal attempts (../../etc/passwd)
3. Test secret pattern detection (fake API keys)
4. Test blocked command patterns
5. Each test prints PASS/FAIL with description

### Defensive Test 2: Secret Scanner (`tests/defensive/test_secret_scanner.py`)

**Tests**:
1. Create temp files with fake secrets, verify scanner detects them
2. Test all patterns: sk-, AKIA, ghp_, xoxb-, -----BEGIN
3. Test clean files pass without false positives
4. Test .gitignore patterns are respected

## Acceptance Criteria (ISC)

- [ ] Session start hook displays active tasks clearly | Verify: run manually
- [ ] Security validator blocks all constitutional rule violations | Verify: test suite
- [ ] Security validator allows legitimate commands through | Verify: test suite
- [ ] Learning capture creates properly formatted signal files | Verify: check output files
- [ ] All defensive tests pass with zero false negatives | Verify: run test suite
- [ ] All scripts run on Python 3.12 Windows | Verify: execute on this machine
- [ ] No external dependencies required (stdlib only) | Verify: import check
