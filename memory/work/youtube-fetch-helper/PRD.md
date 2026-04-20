---
title: youtube_fetch() Helper + Skill Wiring
slug: youtube-fetch-helper
status: DRAFT
created: 2026-04-19
related-prds: memory/work/youtube-transcript-supadata/PRD.md
---

## OVERVIEW

A centralized `tools/youtube.py` module providing `youtube_fetch(video_id) -> TranscriptResult` via `youtube-transcript-api`, replacing the broken Tavily/WebFetch YouTube extraction path across `/absorb`, `/extract-wisdom`, and `/analyze-claims`. Ships with a sanitization gate (HTML strip, VTT artifact removal, 25k char cap, UTF-8 validation) and typed returns (`transcript` | `unavailable`) that eliminate silent degradation. Each skill implements its own routing on `unavailable` state. `yt-dlp` is explicitly excluded pending resolution of upstream POT token issue #13075.

## PROBLEM AND GOALS

- Three skills silently return video descriptions or empty content as transcripts — no typed return, ≥200-char check passes on descriptions
- `/absorb` SKILL.md explicitly claims "tavily_extract handles YouTube transcript extraction" — false for non-viral content
- `youtube-transcript-api` v1.2.4 installed and importable but unwired; fix prescribed in `large-extract-pattern.md` since initial design
- Transcript content enters LLM context unsanitized — attacker-controlled captions create prompt injection surface

## NON-GOALS

- Supadata.ai zero-caption fallback (PRD-2: `memory/work/youtube-transcript-supadata/PRD.md`, ships after 7-day validation window)
- `yt-dlp` integration (blocked: POT token issue #13075, unresolved since May 2025)
- YouTube Data API v3 captions (requires OAuth — unusable for third-party extraction)
- Whisper audio transcription
- Cloud IP proxy configuration (steering doc note in `platform-specific.md` only)

## USERS AND PERSONAS

- Jarvis agent (Claude instance executing a skill) — primary consumer of `youtube_fetch()` output
- Eric — submits YouTube URLs to `/absorb`, `/extract-wisdom`, `/analyze-claims`

## USER JOURNEYS OR SCENARIOS

1. Eric submits YouTube URL to `/absorb` → skill extracts video ID → `python tools/youtube.py <id>` → `{"type": "transcript", ...}` → proceeds with transcript as primary input
2. Video has no captions → returns `{"type": "unavailable"}` → `/absorb` falls back to corroborating synthesis (WA-1 preserved); `/extract-wisdom` returns partial output with `[TRANSCRIPT UNAVAILABLE]` flag; `/analyze-claims` surfaces explicit user message
3. Crafted/malicious caption arrives → sanitization gate strips HTML, VTT artifacts, truncates to 25k → clean text reaches LLM

## FUNCTIONAL REQUIREMENTS

- FR-001: `tools/youtube.py` callable via Bash: `python tools/youtube.py <video_id>` — outputs JSON `{"type": "transcript"|"unavailable", "content": str, "source": str, "video_id": str}`
- FR-002: Sanitization gate: strip HTML tags, strip VTT artifacts (`&gt;&gt;`, `HH:MM:SS.mmm` timestamps), truncate to 25,000 chars, validate UTF-8 encoding
- FR-003: All error paths (network error, invalid ID, IP block, timeout) return `{"type": "unavailable", "source": "<error context>"}` — no unhandled exceptions, 10-second timeout guard
- FR-004: `/absorb` SKILL.md — replace YouTube path with `python tools/youtube.py <id>`; on `unavailable`: attempt corroborating synthesis; remove false claim at line 73
- FR-005: `/extract-wisdom` SKILL.md — replace `tavily_extract` → `tavily_search` YouTube fallback with `youtube_fetch()`; on `unavailable`: return partial structured output with `[TRANSCRIPT UNAVAILABLE]` flag
- FR-006: `/analyze-claims` SKILL.md — same Tavily replacement; on `unavailable`: surface "No transcript available for this video — claims analysis requires transcript content"

## NON-FUNCTIONAL REQUIREMENTS

- No new Python dependencies required (`youtube-transcript-api` v1.2.4 already installed)
- Script completes within 10 seconds for any single video ID
- No subprocess spawn within `tools/youtube.py` — Python import only

## ACCEPTANCE CRITERIA

- [x] `tools/youtube.py` exists and `python tools/youtube.py dQw4w9WgXcQ` returns JSON with `type == "transcript"` | Verify: `python tools/youtube.py dQw4w9WgXcQ | python -c "import sys,json; d=json.load(sys.stdin); assert d['type']=='transcript'; print('PASS')"` [E][M] | model: haiku |
- [x] Output `content` ≤ 25,000 chars for any video | Verify: `python tools/youtube.py dQw4w9WgXcQ | python -c "import sys,json; d=json.load(sys.stdin); assert len(d['content'])<=25000; print('PASS')"` [E][M] | model: haiku |
- [x] Output `content` contains no HTML tags or VTT `&gt;&gt;` artifacts | Verify: `python tools/youtube.py dQw4w9WgXcQ | python -c "import sys,json,re; d=json.load(sys.stdin); assert not re.search(r'<[^>]+>',d['content']); assert '&gt;>' not in d['content']; print('PASS')"` [E][M] | model: haiku |
- [x] `python tools/youtube.py INVALIDID000` returns JSON with `type == "unavailable"` without traceback | Verify: `python tools/youtube.py INVALIDID000 | python -c "import sys,json; d=json.load(sys.stdin); assert d['type']=='unavailable'; print('PASS')"` [E][M] | model: haiku |
- [x] No `tavily_extract`, `tavily_search`, or `WebFetch` calls remain for YouTube URLs in any of the 3 skill SKILL.md files | Verify: `grep -rn "tavily_extract\|tavily_search" .claude/skills/absorb/ .claude/skills/extract-wisdom/ .claude/skills/analyze-claims/ | grep -i youtube` returns empty [E][A] **Anti-criterion** | model: haiku |
- [x] `/absorb` SKILL.md no longer claims "tavily_extract handles YouTube transcript extraction" | Verify: `grep -c "tavily_extract handles YouTube" .claude/skills/absorb/SKILL.md` outputs `0` [E][A] **Anti-criterion** | model: haiku |
- [x] `python tools/youtube.py ""` and `python tools/youtube.py FAKE` both return JSON without Python traceback | Verify: both commands produce valid JSON with `type == "unavailable"` [E][M] **Anti-criterion** | model: haiku |

**ISC Quality Gate: PASS (6/6)**

## SUCCESS METRICS

- ≥80% of YouTube URL submissions to all 3 skills return `type: "transcript"` (baseline: 0% today)
- Zero description-as-transcript incidents after deploy
- No unhandled exceptions from `tools/youtube.py` in any skill session log

## OUT OF SCOPE

- Supadata fallback (PRD-2)
- yt-dlp wiring
- YouTube MCP server

## DEPENDENCIES AND INTEGRATIONS

- `youtube-transcript-api` v1.2.4 (installed, no install step needed)
- `.claude/skills/absorb/SKILL.md`
- `.claude/skills/extract-wisdom/SKILL.md`
- `.claude/skills/analyze-claims/SKILL.md`
- `tools/youtube.py` (new file)
- `orchestration/steering/platform-specific.md` (cloud IP warning note — side effect)

## RISKS AND ASSUMPTIONS

### Risks

- Home IP rate limiting (429) on high-volume use — no mitigation in this PRD; Supadata is PRD-2's job
- Live network dependency in ISC verify tests — tests require internet access; if air-gapped CI, pre-cache fixture

### Assumptions

- `youtube-transcript-api` v1.2.4 works without API key on Eric's home Windows IP (confirmed: evidence agent, HIGH confidence)
- Skills are SKILL.md markdown files consumed by Claude agents executing via Bash — `python tools/youtube.py` is callable from within any skill session
- PRD-2 ships AFTER this PRD is validated for 7 days; safety-net does not ship in parallel with root-cause fix

## OPEN QUESTIONS

- OQ1: ISC verify tests use `dQw4w9WgXcQ` (Rickroll, captioned since 2009) — stable enough for CI, or pre-cache a fixture JSON to remove network dependency entirely?
