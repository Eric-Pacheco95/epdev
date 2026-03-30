# Memory System

2-tier persistent memory modeled on PAI's warm/cold architecture. Session transcripts are indexed directly from Claude Code's native JSONL files (`~/.claude/projects/`) via FTS5.

## Tiers

### Work (Warm) — `memory/work/`
- Active project state, PRDs, task tracking
- One directory per active project: `memory/work/{project-slug}/`
- Each project contains: `PRD.md`, `STATE.md`, `NOTES.md`
- Updated continuously during work

### Learning (Cold) — `memory/learning/`
- Accumulated wisdom, patterns, and institutional knowledge
- Three sub-tiers:

#### Failures — `memory/learning/failures/`
- What went wrong, root cause analysis, fix applied
- Format: `YYYY-MM-DD_{slug}.md`
- Template:
  ```
  # Failure: {title}
  - Date: {date}
  - Severity: {1-10}
  - Context: {what was happening}
  - Root Cause: {why it failed}
  - Fix Applied: {what was done}
  - Prevention: {how to prevent recurrence}
  ```

#### Signals — `memory/learning/signals/`
- Raw observations from sessions, rated 1-10 for significance
- Format: `YYYY-MM-DD_{slug}.md`
- Template:
  ```
  # Signal: {title}
  - Date: {date}
  - Rating: {1-10}
  - Category: {pattern|insight|anomaly|improvement}
  - Observation: {what was noticed}
  - Implication: {why it matters}
  ```

#### Synthesis — `memory/learning/synthesis/`
- Periodic distillation of signals into actionable knowledge
- Created weekly or when signal count exceeds threshold
- Format: `YYYY-MM-DD_synthesis.md`

## Learning Capture Protocol

After every significant task:
1. Rate the outcome (1-10)
2. Identify signals worth capturing
3. Log failures if any
4. Check if synthesis is due (>10 unprocessed signals)
