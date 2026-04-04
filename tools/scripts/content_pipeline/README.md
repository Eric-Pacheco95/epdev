# Building Jarvis -- Substack Content Pipeline

Automated weekly pipeline that collects high-signal material from the Jarvis AI brain,
transforms it into a Substack draft post via claude -p, and routes it for human review
before publishing.

## What It Does

1. **COLLECT** (`collect_sources.py`) -- Scans Jarvis memory for publishable material:
   - Signals rated >= 7, written within the last 7 days
   - Synthesis documents from the last 7 days
   - Architecture review outputs from the last 14 days
   - Research briefs from the last 14 days
   - Runs a safety filter on every file; any file containing employer/bank keywords is skipped and logged

2. **TRANSFORM** (`transform_content.py`) -- Calls `claude -p` with collected sources and
   generates a single Substack draft post (title, subtitle, 3-bullet TL;DR, 400-600 word body).
   Writes the draft to `staging/draft_YYYYMMDD.md`.

3. **REVIEW GATE** (`review_gate.py`) -- Posts the draft to Slack `#content-drafts` for
   human review. Logs every review request to `staging/review_log.json`.

## Directory Structure

```
content_pipeline/
    pipeline.py            -- Orchestrator (run this)
    collect_sources.py     -- Step 1: collect source material
    transform_content.py   -- Step 2: generate draft via claude -p
    review_gate.py         -- Step 3: post to Slack for review
    README.md              -- This file
    staging/
        .gitkeep           -- Keeps staging/ tracked without content
        weekly_sources.json  -- Output of collect step (overwritten weekly)
        draft_YYYYMMDD.md  -- Generated draft posts
        review_log.json    -- Audit trail of review requests
```

## How to Run Manually

```
cd C:\Users\ericp\Github\epdev
python tools/scripts/content_pipeline/pipeline.py
```

Or run individual steps:

```
python tools/scripts/content_pipeline/collect_sources.py
python tools/scripts/content_pipeline/transform_content.py
python tools/scripts/content_pipeline/review_gate.py
```

## Task Scheduler Setup (Weekly, Saturday 9am)

1. Open Task Scheduler
2. Create Basic Task
3. Name: "Jarvis Substack Pipeline"
4. Trigger: Weekly, Saturday, 9:00 AM
5. Action: Start a program
   - Program: `C:\Users\ericp\AppData\Local\Programs\Python\Python311\python.exe`
   - Arguments: `C:\Users\ericp\Github\epdev\tools\scripts\content_pipeline\pipeline.py`
   - Start in: `C:\Users\ericp\Github\epdev`
6. Conditions: uncheck "Start only if on AC power" if on laptop
7. Settings: check "Run task as soon as possible after scheduled start is missed"

Smoke-test the scheduled task by right-clicking and choosing "Run" in Task Scheduler.
Do NOT smoke-test from within an active Claude Code session (subprocess contention).

## Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `SLACK_BOT_TOKEN` | Optional | xoxb-... bot token. If missing, review_gate skips Slack but still logs locally. |
| `ANTHROPIC_API_KEY` | Required | Used by `claude -p` in transform_content.py. Must be set in the Task Scheduler environment. |

To set env vars for Task Scheduler, add them to the system environment variables:
  Control Panel -> System -> Advanced -> Environment Variables

## Safety Filter

Every collected file is checked against these keywords (case-insensitive):

```
TD, bank, Bank, employer, work laptop, client, confidential, MNPI, material
```

If any keyword is found, the file is **skipped entirely** -- it is not included in the
source material sent to claude -p. Skipped files are logged in `weekly_sources.json`
under the `"skipped"` array with the matching keyword noted as the reason.

This prevents any work/employer-related content from entering the publishing pipeline.

## Promoting a Draft to Published

Current workflow (manual Substack paste):

1. Open the draft: `staging/draft_YYYYMMDD.md`
2. Review and edit as needed in any text editor
3. Go to substack.com, create a new post
4. Paste the body content
5. Set title and subtitle from the frontmatter
6. Schedule or publish

Future: Substack API integration when available. The `status: draft` frontmatter field
is reserved for that automation path.

## Content Angles

The pipeline generates posts in one of two modes (claude -p chooses based on source material):

- **Build-in-public**: What was built this week, what problems were solved,
  what steering rules were added. Narrative format.
- **Framework/mental model**: A generalizable insight extracted from the work
  that applies beyond this specific project. Principle-first format.

Target audience: AI systems designers, technical builders, ops-oriented professionals.
Voice: direct, builder-to-builder, no hype, show don't tell.
