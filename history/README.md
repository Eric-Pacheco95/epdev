# History System

Immutable audit trail for all significant events. History files are append-only.

## Decisions — `history/decisions/`

Every significant decision gets logged with rationale.

Format: `YYYY-MM-DD_{slug}.md`

Template:
```markdown
# Decision: {title}
- Date: {date}
- Context: {what prompted this decision}
- Options Considered:
  1. {option A} — pros/cons
  2. {option B} — pros/cons
- Decision: {what was chosen}
- Rationale: {why}
- Reversibility: {easy|moderate|hard|irreversible}
- Review Date: {when to revisit}
```

## Changes — `history/changes/`

Code and configuration change records.

Format: `YYYY-MM-DD_{slug}.md`

Template:
```markdown
# Change: {title}
- Date: {date}
- Files Modified: {list}
- Type: {feature|fix|refactor|config|security}
- Summary: {what changed}
- Reason: {why}
- Tests: {what was verified}
```

## Security — `history/security/`

Security event audit trail.

Format: `YYYY-MM-DD_{slug}.md`

Template:
```markdown
# Security Event: {title}
- Date: {date}
- Severity: {info|low|medium|high|critical}
- Type: {injection-attempt|secret-exposure|unauthorized-access|anomaly}
- Description: {what happened}
- Action Taken: {response}
- Prevention: {how to prevent recurrence}
```
