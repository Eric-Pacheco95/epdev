---
name: capture-recording
description: Analyze guitar recordings with AI feedback mapped to musical goals
---

# IDENTITY and PURPOSE

Guitar recording analysis skill. Pipeline: load MUSIC.md context → Gemini analysis via Python CLI → write to recordings archive → update practice log → log token usage.

# DISCOVERY

## Stage
BUILD

## Syntax
/capture-recording <file_or_directory> [--solo|--band|--batch]

## Parameters
- file_or_directory: path to audio/video file or directory (required)
- --solo: solo practice (default)
- --band: band recording, lead guitar focus
- --batch: all files in directory + cross-recording synthesis

## Examples
- /capture-recording memory/work/telos/recordings/practice_session.mp3
- /capture-recording memory/work/telos/recordings/live_gig.webm --band
- /capture-recording memory/work/telos/recordings/smoke-tests/ --batch

## Chains
- Before: (standalone)
- After: /telos-update (if analysis reveals new development areas)
- Full: /capture-recording > /telos-update (if music development areas identified) > /learning-capture

## Output Contract
- Input: audio/video path + mode
- Output: analysis markdown, MUSIC.md updated, token_log.jsonl entry
- Side effects: Gemini Files API upload (deleted immediately after)

## autonomous_safe
false

## Supported Formats
mp3, wav, aiff, aac, ogg, flac, webm, mp4, m4a

# STEPS

## Step 0: INPUT VALIDATION

- No input: print DISCOVERY, STOP
- File not found: print error, STOP
- Unsupported format: list supported formats, STOP
- Directory without --batch: auto-enable batch, inform user

## Step 1: LOAD CONTEXT

Read `memory/work/telos/MUSIC.md`: Current Development Areas table, Heroes list, Player Profile. These provide context for the `--context` flag.

## Step 2: RUN ANALYSIS

```bash
python tools/scripts/analyze_recording.py <file_or_dir> --<mode> --context memory/work/telos/MUSIC.md 2>analysis_meta.tmp
```

Modes: `--solo` (default), `--band`, `--batch`. Capture stdout (analysis markdown) and stderr (JSON metadata).

## Step 3: WRITE OUTPUT

Single: write to `memory/work/telos/recordings/analyses/{YYYY-MM-DD}_{stem}.md`
Batch: script writes `batch_results.json` + `synthesis_{date}.md` — verify existence.

## Step 4: UPDATE MUSIC.MD

Append row to Recordings table: `| {date} | {filename} | {type} | {level} | {key feedback} |`
Extract level and key feedback from analysis. Dedup: skip if same filename+date exists.

## Step 5: LOG TOKENS

Append to `memory/work/telos/recordings/analyses/token_log.jsonl`:
`{"date": "YYYY-MM-DD", "file": "name", "mode": "solo|band|batch", "model": "...", "tokens": N, "time_s": N, "timestamp": "ISO8601"}`

## Step 6: REPORT

Summary: analysis path, key finding, tokens, MUSIC.md updated, token log updated. Batch: files analyzed count + synthesis path.

# ERROR HANDLING

| Error | Response |
|-------|----------|
| No GEMINI_API_KEY | "Set GEMINI_API_KEY in .env" |
| API error | Script retries once; report if still failing |
| File > 2GB | "Exceeds Gemini limit. Trim or split." |
| Guitar inaudible | Suggest stem separation or closer recording |

# SECURITY

- GEMINI_API_KEY loaded from .env, never logged
- Uploaded files deleted immediately (48h TTL backup)
- No audio content in logs — only analysis text

# VERIFY

- Analysis file written to expected path (recordings/analyses/{date}_{stem}.md) | Verify: Check output for file path confirmation
- MUSIC.md Recordings table updated with new row (date, filename, type, level, feedback) | Verify: tail -3 memory/work/telos/MUSIC.md
- Token log entry appended to token_log.jsonl | Verify: tail -1 memory/work/telos/recordings/analyses/token_log.jsonl
- No GEMINI_API_KEY value appears in analysis file or logs | Verify: grep -c GEMINI_API_KEY memory/work/telos/recordings/analyses/token_log.jsonl
- Batch synthesis file written when --batch flag used | Verify: Check batch_results.json and synthesis_{date}.md existence

# LEARN

- If the same technical weakness (timing, dynamics, bends) appears in 3+ consecutive analyses, surface it to Eric as a focus area via /telos-update
- Track token cost per recording in token_log.jsonl -- if cost per session exceeds expected range, note in /learning-capture
- If audio quality issues (guitar inaudible, clipping) appear frequently, suggest setup improvements in the analysis
- If batch synthesis reveals recurring themes across sessions, capture as a learning signal

# INPUT

INPUT:
