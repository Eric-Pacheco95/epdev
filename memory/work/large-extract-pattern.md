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
- Selection: top view count OR explicit human pick
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

## Tooling baseline

- `yt-dlp` for video metadata + subtitle fetch
- `youtube-transcript-api` for transcript-only fallback
- `mcp__tavily__tavily_extract` for web-article corpora
- Standard LLM extraction via existing `/extract-wisdom` or `/extract-alpha` skills

## First-use log

- 2026-04-19: TheCodingGopher channel — added to sources.yaml tier 1; bounded first slice (5 videos) pending. Tasklist entry under Active.
