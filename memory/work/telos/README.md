# TELOS System — Eric P (epdev)

> Your identity, purpose, and self-knowledge — structured for Jarvis to load, reference, and update.
> Last updated: 2026-03-27

## How TELOS Works

TELOS is your **living identity document**. Unlike static config, these files evolve based on your inputs — voice sessions, Claude Code sessions, Notion notes, and anything else Jarvis can capture.

### Notion integration (ideal state)

- **Jarvis reads Notion for context** when MCP (or a future workflow) is connected — useful for capture that never hit the repo.
- **Writes to repo first for TELOS:** updates land in `memory/work/telos/*.md` from **merged** understanding (Notion + session + chat). Notion does not silently overwrite canonical markdown.
- **Selective write back to Notion** only when a workflow explicitly allows it (e.g. approved mirror or summary page).
- **Read-heavy, selective write** keeps git-markdown as the durable system of record while Notion stays a flexible capture surface.

### The Chain

Every project traces back to a core problem:

```
PROBLEMS → MISSION → NARRATIVES → GOALS → CHALLENGES → STRATEGIES → PROJECTS
```

If a project can't trace back to a problem, question whether it belongs.

### Update Rules

1. **Jarvis proposes, Eric approves** — The `telos-update` skill suggests changes; you review and accept
2. **LEARNED.md and STATUS.md** update most frequently (session-level)
3. **MISSION.md and BELIEFS.md** update rarely (only when something fundamental shifts)
4. **WRONG.md** is append-only — never delete admissions of past errors
5. **All changes are logged** in `history/changes/` with rationale

### File Index

| File | Updated By | Frequency | Purpose |
|------|-----------|-----------|---------|
| MISSION.md | Eric (rare) | Quarterly | The ONE core purpose |
| PROBLEMS.md | Eric | Monthly | Root problems driving everything |
| GOALS.md | Eric + Jarvis | Monthly | Specific goals with weights/metrics |
| CHALLENGES.md | Eric + Jarvis | Monthly | What blocks goals |
| STRATEGIES.md | Eric + Jarvis | Monthly | Playbook for approaching goals |
| PROJECTS.md | Jarvis | Weekly | Active work streams and status |
| IDEAS.md | Eric + Jarvis | Anytime | Opportunity backlog |
| BELIEFS.md | Eric (rare) | Quarterly | Core values and worldview |
| MODELS.md | Eric + Jarvis | Monthly | Mental models and frameworks |
| FRAMES.md | Eric + Jarvis | Monthly | Thinking frameworks applied to situations |
| NARRATIVES.md | Eric | Monthly | Stories you tell yourself |
| LEARNED.md | Jarvis | Every session | What Jarvis discovers about you |
| WISDOM.md | Eric | Anytime | Hard-won life lessons |
| WRONG.md | Eric | Anytime | Things you've been wrong about |
| PREDICTIONS.md | Eric | Anytime | Future predictions with confidence % |
| HISTORY.md | Eric | Rare | Personal background and formative experiences |
| STATUS.md | Jarvis | Every session | Current life state snapshot |
| MUSIC.md | Eric + Jarvis | Monthly | Musical identity, goals, practice |
