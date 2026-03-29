# PRD: /capture-recording — Guitar Recording Analysis Skill

**Date:** 2026-03-28
**Author:** Jarvis (via /create-prd)
**Status:** Implemented
**Prior art:** smoketest_audio_analysis.py, batch_audio_analysis.py (both validated)
**Research:** /first-principles + /find-logical-fallacies + /research --technical (all complete)
**Baseline data:** 10-recording synthesis at `memory/work/telos/recordings/smoke-tests/analyses/synthesis.md`

---

## OVERVIEW

`/capture-recording` is a Jarvis skill that analyzes guitar and music recordings using the Gemini API, producing specific technical feedback mapped to Eric's documented musical goals and development areas. It consists of a SKILL.md orchestration layer (reads MUSIC.md goals, writes outputs, updates practice log) and a thin Python CLI script (handles file upload, Gemini API calls, and markdown generation). Validated across 10 recordings of the Jordan Dias Band — 6 studio demos and 4 live performances — with musically actionable results including key/mode identification, technique-specific feedback, and prioritized exercises.

## PROBLEM AND GOALS

- **Problem:** Eric plays lead guitar in a working band but has no structured feedback loop on his playing. Human guitar teachers are expensive, infrequent, and not available post-gig. Recordings exist (iPhone, YouTube) but sit unanalyzed.
- **Goal 1:** Provide post-session reflective analysis of guitar recordings with technique-specific, actionable feedback (not generic encouragement) — tied to TELOS Goal #3 (Guitar mastery, 15% weight)
- **Goal 2:** Track development over time by building a structured history of analyses against 6 documented development areas (bend intonation, rushing, vibrato, dynamics, chord-tone targeting, chromatic vocabulary)
- **Goal 3:** Dynamically load Eric's current goals and development areas from MUSIC.md so feedback evolves as he improves
- **Goal 4:** Make the feedback loop as low-friction as possible — drop a file, run one command, get analysis + practice log updated

## NON-GOALS

- **Not a real-time practice coach** — this is post-session analysis, not live feedback (Yousician/Fretello own that niche)
- **Not a music production tool** — no mixing, mastering, or arrangement feedback
- **Not a transcription tool** — no tab/notation generation (possible future extension)
- **Not multi-instrumentalist** — focuses on lead guitar analysis; other instruments are context, not targets
- **Not a Google Drive poller** — mobile file ingestion is a separate infrastructure task (Phase 3)

## ACCEPTANCE CRITERIA

### Phase 1 ISC (Ideal State Criteria)

- [x] Python CLI script `tools/scripts/analyze_recording.py` exists and runs standalone | Verify: `python tools/scripts/analyze_recording.py --help` exits 0 `[M]`
- [x] SKILL.md at `.claude/skills/capture-recording/SKILL.md` exists with DISCOVERY section | Verify: file exists with required sections `[A]`
- [x] `--solo` mode produces structured analysis with all required sections | Verify: run on studio_movin_on.webm, check output has Style, Technique, Strengths, Improvement, Assessment sections `[M]`
- [x] `--band` mode produces analysis focused on lead guitar with mix observation | Verify: run on live_lily_pad.webm, check output has Mix Observation section `[M]`
- [x] Development areas from MUSIC.md appear in the system prompt | Verify: add debug flag `--show-prompt`, confirm MUSIC.md content in prompt `[M]`
- [x] Analysis file written to `memory/work/telos/recordings/analyses/` with correct naming | Verify: file exists at `{date}_{stem}.md` after analysis `[M]`
- [x] MUSIC.md practice log updated with one-line summary | Verify: grep for new filename in MUSIC.md recordings table `[M]`
- [x] Token usage logged to `token_log.jsonl` | Verify: new JSONL entry after analysis `[M]`
- [x] `--batch` mode analyzes all files in directory and produces synthesis | Verify: run on smoke-tests directory, check batch_results.json + synthesis file `[M]`
- [x] Uploaded files deleted from Gemini after analysis | Verify: metadata JSON shows gemini_file_deleted: true `[M]`
- [x] All error cases produce readable messages (file not found, bad format, no API key, API error) | Verify: trigger each case, check output `[M]`
- [x] `/review-code` passes on analyze_recording.py (security: no key leakage, input validation) | Verify: run /review-code `[A]`

## FUNCTIONAL REQUIREMENTS

### Phase 1 (MVP)

**FR-001: Single recording analysis (solo mode)**
- Accept local file path (mp3, wav, aiff, aac, ogg, flac, webm, mp4, m4a)
- Upload to Gemini via Files API with correct MIME type
- Analyze with solo-focused prompt including development areas from MUSIC.md
- Return structured markdown: Style & Influences, Technique Assessment (phrasing, timing, note choice, dynamics, articulation), Strengths, Areas for Improvement (with exercises), Overall Assessment
- Delete uploaded file from Gemini after analysis
- Verify: analysis output contains section headings and specific musical terminology | `[M]`

**FR-002: Single recording analysis (band mode)**
- Same as FR-001 but with band-focused prompt
- Additional section: Overall Mix Observation (guitar prominence, other instruments)
- Quality self-report: if Gemini cannot clearly hear the guitar, output includes a warning and suggests stem separation
- Verify: band mode prompt includes "focus on lead guitar" instruction | `[M]`

**FR-003: Dynamic goal loading from MUSIC.md**
- SKILL.md reads `memory/work/telos/MUSIC.md` at analysis time
- Extracts "Current Development Areas" table and "Heroes" list
- Injects into system prompt as context: "This player's documented development areas are: [list]. Their influences include: [list]."
- Goals are context, NOT evaluation criteria — prompt must NOT say "evaluate against Garcia"
- Verify: system prompt contains current development areas from MUSIC.md | `[A]`

**FR-004: Analysis output file**
- Write full analysis to `memory/work/telos/recordings/analyses/{YYYY-MM-DD}_{filename_stem}.md`
- Include metadata header: date, file, mode, model, token count, duration
- Verify: file exists after analysis with correct naming and metadata | `[M]`

**FR-005: Practice log update**
- Append one-line summary to MUSIC.md "Recordings" table
- Format: `| {date} | {filename} | {type} | {level} | {key feedback} |`
- Verify: MUSIC.md recordings table has new row after analysis | `[M]`

**FR-006: Token usage tracking**
- Log per-analysis: file name, tokens used, model, timestamp
- Append to `memory/work/telos/recordings/analyses/token_log.jsonl`
- Verify: token_log.jsonl has new entry after each analysis | `[M]`

**FR-007: Batch analysis mode**
- Accept directory path, discover all audio files
- Analyze each file individually (JSON structured output for cross-analysis)
- After all files analyzed, run cross-recording synthesis prompt
- Write individual results to `analyses/batch_results.json`
- Write synthesis to `analyses/synthesis_{date}.md`
- Update MUSIC.md "Current Development Areas" if synthesis reveals changed priorities
- Verify: batch_results.json and synthesis file exist after batch run | `[M]`

**FR-008: Error handling**
- File not found → clear error message with path
- Unsupported format → list supported formats
- Gemini API error → retry once, then report error with status code (API key redacted)
- File too large (>2GB) → warn and suggest trimming
- No GEMINI_API_KEY → clear error pointing to .env setup
- Verify: each error case produces a user-readable message | `[M]`

### Phase 2 (Future)

**FR-009: Comparison mode (--compare)**
- Requires 5+ prior analyses in analyses/ directory
- Load historical analyses, compute trends per development area
- New analysis includes progress assessment: "improved / unchanged / regressed" per area

**FR-010: Stem separation preprocessing**
- For band recordings where guitar is quiet, optionally run stem separation before analysis
- Integrate Moises or LALAL.ai API for lead guitar isolation

**FR-011: YouTube URL input**
- Accept YouTube URL instead of file path
- Use yt-dlp to download audio (best quality, no video)

### Phase 3 (Future)

**FR-012: Google Drive watched folder**
- Separate poller script watches Google Drive "Jarvis Drop/recordings/" folder
- Downloads new files to local recordings directory
- Triggers /capture-recording automatically

## NON-FUNCTIONAL REQUIREMENTS

- **Latency:** Single recording analysis completes in <30 seconds for files under 10MB (validated: 10-20s in smoke tests)
- **Cost:** <$0.01 per single-song analysis at Gemini 3 Flash pricing (~6K tokens per 3-min song)
- **Reliability:** Gemini Files API has 48-hour TTL; uploaded files are deleted immediately after analysis
- **Security:** GEMINI_API_KEY loaded from .env, never hardcoded or logged. Exception messages sanitized to redact API keys. No audio content in logs.
- **Encoding:** All file I/O uses UTF-8. Print output uses ASCII only (Windows cp1252 compatibility per steering rule).
- **Idempotency:** Re-analyzing the same file produces a new dated analysis file, does not overwrite previous analyses

## DEPENDENCIES AND INTEGRATIONS

| Dependency | Type | Status |
|-----------|------|--------|
| `google-genai` Python SDK | Library | Installed (v1.69.0) |
| Gemini 3 Flash (`gemini-3-flash-preview`) | API | Active, validated |
| GEMINI_API_KEY in `.env` | Secret | Present |
| `memory/work/telos/MUSIC.md` | Data | Populated with 10-recording baseline |
| `yt-dlp` | Library (Phase 2) | Installed |
| `ffmpeg` | Tool (Phase 2) | Installed via winget |
| Moises/LALAL.ai API | External API (Phase 2) | Not yet researched |
| Google Drive MCP | MCP server (Phase 3) | Wired but not tested |

## RISKS AND ASSUMPTIONS

### Risks
- **Gemini model deprecation:** `gemini-3-flash-preview` may be deprecated. Mitigation: model name as `--model` flag.
- **Analysis quality on poor recordings:** iPhone in noisy venues may produce vague feedback. Mitigation: quality self-report + stem separation in Phase 2.
- **MUSIC.md format drift:** If structure changes, goal loading breaks. Mitigation: parse by section headers, fail gracefully.

### Assumptions
- Gemini 3 Flash's music analysis capability remains stable
- Eric will transfer recordings to desktop regularly
- The 6 development areas from 10 recordings are representative
