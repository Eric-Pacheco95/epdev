---
title: Notion Voice Capture Pipeline
slug: notion-voice-pipeline
status: DRAFT
created: 2026-04-19
---

## OVERVIEW

Closes the voice-capture dead zone in `/notion-sync inbox`. The skill currently explicitly skips voice transcripts (SKILL.md:82). This PRD updates inbox mode to detect and process dictated-text entries from the Inbox's Captures section, and adds a weekly RemoteTrigger so it runs without a manual session.

## PROBLEM AND GOALS

- Voice notes land in Notion Inbox (Captures section) but are never extracted — the skill excludes them by design
- Goal: voice captures surface as Jarvis signals within 7 days, no manual intervention

## NON-GOALS

- No audio transcription — Eric provides pre-transcribed text
- No new Notion pages or sections
- No changes to journal / goals / push modes

## USERS AND PERSONAS

- Eric (sole actor) — dictates to Notion, expects captures to enter signal pipeline automatically

## USER JOURNEYS OR SCENARIOS

1. Eric dictates → text lands in Notion Inbox > Captures section
2. Weekly RemoteTrigger fires `/notion-sync inbox`
3. Captures entries detected and signal-extracted (1–10 rating, same schema as typed entries)
4. Signals written to `memory/learning/signals/` with `Source: notion-voice-capture`
5. Entries marked processed in Notion

## FUNCTIONAL REQUIREMENTS

- FR-001: Inbox mode detects entries in the Captures section of Inbox as voice captures
- FR-002: Voice captures are signal-extracted using the same 1–10 schema as typed entries
- FR-003: Processed Captures entries are marked done in Notion after sync
- FR-004: Signal files for voice captures use `Source: notion-voice-capture`
- FR-005: A weekly RemoteTrigger runs `/notion-sync inbox` on a fixed cadence

## NON-FUNCTIONAL REQUIREMENTS

- Must not degrade existing typed-text inbox processing
- Trigger must fire within the 7-day window (not accumulate unprocessed entries)

## ACCEPTANCE CRITERIA

- [x] `/notion-sync inbox` SKILL.md contains no clause excluding Captures-section entries from processing `[I][A]` | Verify: `grep -n "voice\|transcript\|skip" .claude/skills/notion-sync/SKILL.md` — must return 0 matches for any exclusion logic in inbox mode `| model: haiku |`
- [x] At least one signal file exists in `memory/learning/signals/` with `Source: notion-voice-capture` after a test run `[E][M]` | Verify: `grep -rl "Source: notion-voice-capture" memory/learning/signals/ | wc -l` — must be ≥ 1 `| model: haiku |`
- [x] A RemoteTrigger for `/notion-sync inbox` is registered with a weekly cadence `[E][M]` | Verify: `RemoteTrigger action: list` — output must include a trigger named `jarvis-notion-sync-inbox` with `cron_expression` containing `* * 0` (Sunday) `| model: haiku |`
- [x] Anti-criterion: Inbox mode reads only Inbox page `32fbf5ae-a9e3-8198-9975-cbc6293c8690` — no other page IDs appear in inbox mode step logic `[E][A]` | Verify: Grep SKILL.md inbox mode steps for any page ID not matching the Inbox ID `| model: haiku |`
- [x] Anti-criterion: Raw voice transcript text is absent from `history/changes/notion_sync.md` — only metadata (date, count, source) is logged `[E][A]` | Verify: Read `history/changes/notion_sync.md` log format; confirm no transcript content present `| model: haiku |`

**ISC Quality Gate: PASS (6/6)**

## SUCCESS METRICS

- Voice entries processed within 7-day window: 100%
- Weekly trigger fires without manual session: confirmed after first run

## OUT OF SCOPE

- Routing voice signals to specific Brain pages (Ideas, Music) — signal extraction only; routing is a future step
- Multiple capture types (audio, images)

## DEPENDENCIES AND INTEGRATIONS

- `mcp__claude_ai_Notion` — read/write Inbox page `32fbf5ae-a9e3-8198-9975-cbc6293c8690`
- `/schedule` or `RemoteTrigger` — weekly cadence
- `memory/learning/signals/` — signal output directory

## RISKS AND ASSUMPTIONS

**Risks:**
- Notion MCP structure of Captures section unknown — how it's identified (header block vs. property vs. page title) is the key implementation risk (see OQ1); acceptable fallback is treating all unprocessed Inbox entries as voice captures
- If Captures entries have no machine-detectable boundary, inbox mode processes all unprocessed entries identically (acceptable)

**Assumptions:**
- Eric's voice entries are already transcribed text when they land in Notion
- Weekly cadence is sufficient; 7-day trigger interval matches the processing window

## OPEN QUESTIONS (RESOLVED)

- OQ1 ✅: Captures section is an h2 heading block ("Captures") inside the Inbox page. Entries below it follow: timestamp paragraph (e.g. "Mar 26, 2026 at 8:12 PM") + transcript text paragraph(s). Italic instruction line and divider immediately below heading are non-data — skip them. All paragraphs below the "Captures" heading (until next heading or end of page) are voice capture entries.
- OQ2 ✅: No preference → Sunday 10pm ET (weekly cadence).
