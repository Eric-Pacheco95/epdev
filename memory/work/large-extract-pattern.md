# Large-Corpus Extraction Pattern (working notes)

> Status: WORKING NOTES — not a skill yet. Promote to `/create-pattern` after 2nd successful use per CLAUDE.md frequency gate.
> First use: TheCodingGopher channel retro extraction (2026-04-19).

## Problem

Large corpora (YouTube channels, podcast archives, paper sets, book series) contain high-value domain knowledge but cannot be extracted in one pass:
- Unbounded token cost
- Rate limits on batch fetches
- Signal dilution from low-value entries (vlogs, intros, meta)
- Premature sub-domain taxonomy commitment from metadata alone

## Pattern: Bounded Slice → Evaluate → Scale

### Phase 1 — Enumerate (metadata-only, cheap)

- `yt-dlp --flat-playlist --dump-json` (or equivalent for other corpora)
- Count items; dump titles + descriptions + view counts + dates
- Output: `memory/work/<corpus>/metadata.jsonl`

### Phase 2 — Bounded first slice (HARD CAP)

- Hard cap: **5 items** on first run
- Selection: top view count OR explicit human pick OR top 3 matching domain-relevant keywords — **not pure view count alone**; for niche channels, viral content and domain-relevant content may not overlap
- Extract full content (transcripts via `yt-dlp --write-auto-subs` or `youtube-transcript-api`)
- Rate limit: `--sleep-interval 2`

### Phase 3 — Evaluate

- Signal quality: does the content justify extraction? (per-item Y/N)
- Cost: tokens consumed vs value
- Clustering: do 3-5 items suggest a coherent sub-domain, or scattered topics?
- Dedup check: does this overlap existing knowledge files (`harness-tooling.md`, `ai-infra/*`)?

### Phase 4 — Decide

- **Stop**: low signal → leave source as tier-1 daily monitor only, archive metadata
- **Scale with existing home**: high signal, topics overlap existing domain → route to existing file
- **New sub-domain**: high signal, coherent new topic → create `memory/knowledge/<domain>/_context.md` + sub-files
- **Expand slice**: ambiguous → next 10-20 items before deciding taxonomy

## Anti-patterns

- "Iterate through all videos" on first pass — unbounded token cost
- Commit sub-domain taxonomy from titles + descriptions alone — nuance lives in transcripts
- Create new knowledge domain before dedup check — pollution risk
- Promote to SKILL.md after 1st use — CLAUDE.md frequency gate requires 2nd confirming use

## Batch Mode (Overnight Dispatcher)

For channels with 10+ relevant videos, single-session extraction hits the CTX wall at ~3 videos. Use the overnight dispatcher queue instead.

### Architecture

```
Main agent (dispatcher pass)
  ├── Pop 1-2 video IDs from queue file
  ├── Spawn subagent per video (parallel)
  │     each: fetch transcript → extract signal → return ≤200-word JSON summary
  └── Receive summaries → write knowledge files → update queue
```

### Subagent Prompt Template

```
You are a knowledge extraction agent for the Jarvis AI system.

TASK: Extract domain-relevant signal from this YouTube video transcript.

VIDEO_ID: {video_id}
VIDEO_TITLE: {title}
DOMAIN_HINT: {domain}  # e.g. "ai-infra", "crypto", "networking"

TRANSCRIPT:
{transcript_text}

OUTPUT: Return ONLY a JSON object — no prose:
{
  "signal": "HIGH|MEDIUM|LOW",
  "jarvis_relevance": "one sentence — why this matters to Jarvis specifically",
  "routing_decision": "existing:<filename>|new_domain:<name>|stop",
  "extractable_points": [
    "concrete fact or pattern — max 25 words each",
    ...
  ],
  "dedup_risk": "YES|NO — does this overlap existing ai-infra, crypto, or security knowledge?"
}

RULES:
- extractable_points: max 8 items, each must be actionable or architectural (no definitions)
- signal=LOW + no unique points → routing_decision must be "stop"
- Do NOT write files. Return JSON only.
```

### Queue Format

`memory/work/<corpus>/queue.json`:
```json
{ "pending": ["id1", "id2", ...], "processed": [], "written_files": [] }
```

### File-write ownership

Main agent (not subagents) writes all knowledge files. Subagents return JSON only. Prevents duplicate writes and keeps routing centralized.

## Tooling baseline

- `yt-dlp` for video metadata + subtitle fetch
- `youtube-transcript-api` for transcript-only fallback
- `mcp__tavily__tavily_extract` for web-article corpora
- Standard LLM extraction via existing `/extract-wisdom` or `/extract-alpha` skills

## Use log

- 2026-04-19: TheCodingGopher channel — FULL EXTRACTION COMPLETE. Phases 1-4 + expand-slice executed. Decision: ROUTE TO EXISTING AI-INFRA (no new sub-domain). 7 videos evaluated (5 top-by-views + 2 AI-targeted). Produced: `ai-infra/2026-04-19_mcp-protocol.md` (HIGH signal), `ai-infra/2026-04-19_postgres-unified-backend.md` (MEDIUM signal). Key lesson: top-5-by-views missed all AI content; keyword-filter selection corrected above. Full evaluation: `memory/work/thecodinggopher/evaluation.md`.
- 2026-04-19 Phase 1 COMPLETE: Andrej Karpathy (`@AndrejKarpathy`) — 17 videos enumerated, 12 queued (5 excluded: stable diffusion visual clips). Queue written to `memory/work/karpathy/queue.json`. Evaluation stub at `memory/work/karpathy/evaluation.md`. Note: `--flat-playlist` view_count is null in saved JSONL; live output captured top-5 counts (range 1.1M–6.1M). Phases 2-4 pending overnight dispatcher. On Phase 4 complete: promote to `/create-pattern`.
