"""
analyze_recording.py -- Gemini-powered guitar recording analysis.

Thin CLI: file in, structured markdown analysis out. No side effects.
Orchestration (MUSIC.md updates, file writing) handled by SKILL.md.

Usage:
    python tools/scripts/analyze_recording.py <file_or_dir> [options]

Options:
    --solo          Solo practice recording (default)
    --band          Full band recording, focus on lead guitar
    --batch         Analyze all audio files in a directory + synthesis
    --model MODEL   Gemini model (default: gemini-3-flash-preview)
    --context FILE  Path to MUSIC.md for dynamic goal loading
    --show-prompt   Print the constructed system prompt (debug)
    --json          Output JSON instead of markdown (for batch individual)
    --help          Show this help
"""

import sys
import os
import re
import time
import json
import datetime
from pathlib import Path

# Load .env from epdev root
_env_path = Path(__file__).resolve().parents[2] / ".env"
if _env_path.exists():
    with open(_env_path, "r", encoding="utf-8") as _f:
        for _line in _f:
            _line = _line.strip()
            if _line and not _line.startswith("#") and "=" in _line:
                _k, _, _v = _line.partition("=")
                os.environ.setdefault(_k.strip(), _v.strip().strip('"').strip("'"))

from google import genai
from google.genai import types

# -- Constants --

DEFAULT_MODEL = "gemini-3-flash-preview"
EVENTS_DIR = Path(__file__).resolve().parents[2] / "history" / "events"


def _log_gemini_usage(model: str, usage_metadata, context: str = "") -> None:
    """Log Gemini API token usage to the event JSONL for cost tracking."""
    try:
        EVENTS_DIR.mkdir(parents=True, exist_ok=True)
        today = datetime.date.today().isoformat()
        event_file = EVENTS_DIR / f"{today}.jsonl"
        record = {
            "ts": datetime.datetime.now(datetime.timezone.utc).strftime(
                "%Y-%m-%dT%H:%M:%SZ"
            ),
            "type": "gemini_usage",
            "model": model,
            "input_tokens": getattr(usage_metadata, "prompt_token_count", None),
            "output_tokens": getattr(usage_metadata, "candidates_token_count", None),
            "total_tokens": getattr(usage_metadata, "total_token_count", None),
            "context": context,
            "source": "analyze_recording.py",
        }
        import msvcrt
        with open(event_file, "a", encoding="utf-8") as f:
            msvcrt.locking(f.fileno(), msvcrt.LK_LOCK, 1)
            f.write(json.dumps(record, ensure_ascii=True) + "\n")
            msvcrt.locking(f.fileno(), msvcrt.LK_UNLCK, 1)
    except Exception:
        pass  # best-effort -- never break the main flow

SUPPORTED_EXTS = {".mp3", ".wav", ".aiff", ".aac", ".ogg", ".flac", ".webm", ".mp4", ".m4a"}

MIME_MAP = {
    ".mp3": "audio/mp3", ".wav": "audio/wav", ".aiff": "audio/aiff",
    ".aac": "audio/aac", ".ogg": "audio/ogg", ".flac": "audio/flac",
    ".mp4": "video/mp4", ".m4a": "audio/m4a", ".webm": "audio/webm",
}

LONG_RECORDING_WARN_SECONDS = 600  # 10 minutes

BASE_SYSTEM_PROMPT = """You are an expert guitar instructor and music analyst with deep knowledge of:
- Improvisational guitar styles (Jerry Garcia, John Mayer, jazz, funk, Grateful Dead tradition)
- Music theory (scales, modes, chord-scale relationships, voice leading)
- Guitar technique (phrasing, dynamics, vibrato, bending, legato, picking articulation)
- Rhythm and timing (behind/ahead of beat feel, groove, swing)
- Tone and sound design (amp tones, effects, clean vs driven)

Your job is to analyze audio recordings of guitar playing and provide SPECIFIC, ACTIONABLE feedback.
Do NOT give generic encouragement. Be honest and technical.
Reference specific musical concepts by name."""

SOLO_PROMPT = """Analyze this solo guitar recording. Provide structured feedback:

## Style & Influences
- What genre/style does this playing evoke?
- Which known guitarists does this remind you of, and why specifically?

## Technique Assessment
- **Phrasing**: How are musical ideas constructed? Are phrases complete or fragmented?
- **Timing/Rhythm**: Is the timing tight or loose? Behind the beat, on top, or rushing?
- **Note Choice**: What scales/modes are being used? Any interesting or weak note choices over the harmony?
- **Dynamics**: Is there dynamic range or is it flat?
- **Articulation**: Picked vs legato? Vibrato quality? Bend accuracy?

## Strengths (be specific)
- What is this player doing WELL? Name concrete examples.

## Areas for Improvement (be specific and actionable)
- What specific things should this player practice to improve?
- Suggest 2-3 concrete exercises or approaches.

## Overall Assessment
- Rate the playing level (beginner/intermediate/advanced-intermediate/advanced/professional)
- One sentence summary of the most important thing to work on next."""

BAND_PROMPT = """Analyze this band recording, focusing specifically on the LEAD GUITAR playing.
Note: this is a full band recording -- try to focus your analysis on the guitar parts.
If you cannot clearly hear the lead guitar in the mix, say so explicitly and suggest stem separation.

## Overall Mix Observation
- Can you clearly hear the lead guitar? How prominent is it in the mix?
- What other instruments are present?

## Lead Guitar Analysis
- **Style & Influences**: What style is the guitarist playing? Any artist similarities?
- **Phrasing**: How are solos/lead lines constructed?
- **Timing with the band**: Is the guitarist locking in with the rhythm section?
- **Note Choice**: Scales, modes, interesting choices over chord changes?
- **Tone**: Describe the guitar tone as best you can hear it.
- **Role in the arrangement**: Is the guitarist serving the song or overplaying?

## Strengths (be specific)

## Areas for Improvement (be specific and actionable)
- What should this guitarist practice?

## Overall Assessment
- Rate the playing level (beginner/intermediate/advanced-intermediate/advanced/professional)
- One sentence: most important thing to work on next."""

BATCH_JSON_PROMPT = """Analyze the lead guitar in this recording. Output ONLY this JSON structure:
{
  "song": "<song name if identifiable, else 'Unknown'>",
  "style": "<primary genre/style>",
  "influences": ["<detected artist similarities>"],
  "key_and_mode": "<detected key and mode>",
  "playing_level": "<beginner|intermediate|advanced-intermediate|advanced|professional>",
  "strengths": ["<specific strength 1>", "<specific strength 2>"],
  "weaknesses": ["<specific weakness 1>", "<specific weakness 2>"],
  "tone_description": "<brief tone description>",
  "timing": "<tight|on-top|behind|rushing|loose>",
  "top_exercise": "<single most important practice recommendation>"
}
Output valid JSON only, no markdown formatting."""

SYNTHESIS_PROMPT = """You are an expert guitar instructor who has just analyzed {count} recordings
from the same guitarist. Here are the individual analyses:

{analyses}

Provide a COMPREHENSIVE SYNTHESIS:

## Player Profile
- Overall playing level
- Primary style identity and influences
- Signature strengths across multiple recordings

## Consistent Patterns (things in 3+ recordings)
- Recurring strengths with examples
- Recurring weaknesses with examples
- Tone preferences and rhythmic tendencies

## Development Priority Stack (ordered by impact)
1. (highest impact) -- WHY + ONE exercise
2.
3.
4.
5.

## Studio vs Live Comparison
- How does playing change between contexts?
- Technique that holds up vs degrades?

## Style Evolution Recommendations
Based on stated influences:
- Specific techniques to study from each influence
- What vocabulary would unlock the next level?

Be brutally honest. This guitarist wants to improve, not be flattered."""


# -- MUSIC.md parsing --

def load_music_context(music_md_path):
    """Extract development areas and heroes from MUSIC.md."""
    if not music_md_path or not os.path.exists(music_md_path):
        return None

    with open(music_md_path, "r", encoding="utf-8") as f:
        content = f.read()

    context_parts = []

    # Extract heroes
    heroes_match = re.search(r"\*\*Heroes\*\*:\s*(.+)", content)
    if heroes_match:
        context_parts.append(
            f"This player's musical influences include: {heroes_match.group(1).strip()}"
        )

    # Extract development areas table
    dev_section = re.search(
        r"## Current Development Areas.*?\n(.*?)(?=\n## |\Z)",
        content, re.DOTALL
    )
    if dev_section:
        rows = re.findall(r"\|\s*\d+\s*\|([^|]+)\|([^|]+)\|", dev_section.group(1))
        if rows:
            areas = [f"{area.strip()}: {finding.strip()}" for area, finding in rows]
            context_parts.append(
                "This player's documented development areas (ordered by priority):\n"
                + "\n".join(f"  - {a}" for a in areas)
            )

    # Extract player profile
    profile_section = re.search(
        r"## Player Profile.*?\n(.*?)(?=\n## |\Z)",
        content, re.DOTALL
    )
    if profile_section:
        context_parts.append(
            f"Player profile:\n{profile_section.group(1).strip()}"
        )

    if not context_parts:
        return None

    return (
        "\n\nCONTEXT ABOUT THIS PLAYER (use as background, not as evaluation criteria):\n"
        + "\n\n".join(context_parts)
    )


# -- Core analysis --

def get_api_key():
    key = os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
    if not key:
        print("ERROR: No GEMINI_API_KEY or GOOGLE_API_KEY found.")
        print("Set it in your .env file at the project root.")
        sys.exit(1)
    return key


def upload_and_wait(client, file_path):
    """Upload file to Gemini Files API, wait for processing, return file object."""
    ext = Path(file_path).suffix.lower()
    mime_type = MIME_MAP.get(ext)
    config = {"mime_type": mime_type} if mime_type else {}

    uploaded = client.files.upload(file=file_path, config=config)

    while uploaded.state.name == "PROCESSING":
        time.sleep(2)
        uploaded = client.files.get(name=uploaded.name)

    if uploaded.state.name == "FAILED":
        print(f"ERROR: Gemini failed to process file: {file_path}")
        sys.exit(1)

    return uploaded


def cleanup_file(client, uploaded):
    """Delete uploaded file from Gemini."""
    try:
        client.files.delete(name=uploaded.name)
        return True
    except Exception:
        return False


def analyze_single(client, file_path, mode, model, system_prompt, show_prompt=False):
    """Analyze a single recording. Returns (analysis_text, metadata_dict)."""
    file_size_mb = os.path.getsize(file_path) / (1024 * 1024)
    file_size_bytes = os.path.getsize(file_path)
    ext = Path(file_path).suffix.lower()
    stem = Path(file_path).stem

    # File size check
    if file_size_bytes > 2 * 1024 * 1024 * 1024:
        print(f"ERROR: File is {file_size_mb:.0f}MB -- exceeds Gemini 2GB limit.")
        print("Trim the recording or split into smaller files.")
        sys.exit(1)

    # Duration estimate (rough: 32 tokens/sec, ~16kbps after downsample)
    est_duration_min = (file_size_mb * 8) / (0.128 * 60)  # rough estimate
    if est_duration_min > LONG_RECORDING_WARN_SECONDS / 60:
        print(f"WARNING: Recording is ~{est_duration_min:.0f} minutes.")
        print("Analysis quality is best on single songs (3-6 min). Consider splitting.")
        print()

    if mode == "json":
        prompt = BATCH_JSON_PROMPT
    elif mode == "band":
        prompt = BAND_PROMPT
    else:
        prompt = SOLO_PROMPT

    if show_prompt:
        print("=== SYSTEM PROMPT ===")
        print(system_prompt)
        print("=== ANALYSIS PROMPT ===")
        print(prompt)
        print("=====================")
        print()

    # Upload
    start_upload = time.time()
    uploaded = upload_and_wait(client, file_path)
    upload_time = time.time() - start_upload

    # Analyze
    start_analysis = time.time()
    try:
        response = client.models.generate_content(
            model=model,
            config=types.GenerateContentConfig(
                system_instruction=system_prompt,
                temperature=0.3,
            ),
            contents=[prompt, uploaded],
        )
    except Exception as e:
        cleanup_file(client, uploaded)
        # Retry once -- sanitize error message to avoid leaking API key
        err_msg = str(e)
        api_key = os.environ.get("GEMINI_API_KEY", "") or os.environ.get("GOOGLE_API_KEY", "")
        if api_key and api_key in err_msg:
            err_msg = err_msg.replace(api_key, "[REDACTED]")
        print(f"Gemini API error: {err_msg}. Retrying...", file=sys.stderr)
        time.sleep(2)
        uploaded = upload_and_wait(client, file_path)
        try:
            response = client.models.generate_content(
                model=model,
                config=types.GenerateContentConfig(
                    system_instruction=system_prompt,
                    temperature=0.3,
                ),
                contents=[prompt, uploaded],
            )
        except Exception as e2:
            cleanup_file(client, uploaded)
            err_msg2 = str(e2)
            if api_key and api_key in err_msg2:
                err_msg2 = err_msg2.replace(api_key, "[REDACTED]")
            print(f"ERROR: Gemini API failed after retry: {err_msg2}")
            sys.exit(1)

    analysis_time = time.time() - start_analysis
    tokens = response.usage_metadata.total_token_count
    _log_gemini_usage(model, response.usage_metadata, context="recording_analysis")

    # Cleanup
    deleted = cleanup_file(client, uploaded)

    metadata = {
        "file": stem,
        "file_path": str(file_path),
        "format": ext,
        "size_mb": round(file_size_mb, 1),
        "mode": mode if mode != "json" else "batch",
        "model": model,
        "tokens": tokens,
        "upload_time_s": round(upload_time, 1),
        "analysis_time_s": round(analysis_time, 1),
        "total_time_s": round(upload_time + analysis_time, 1),
        "timestamp": datetime.datetime.now().isoformat(),
        "gemini_file_deleted": deleted,
    }

    return response.text, metadata


def run_single(args):
    """Run single file analysis mode."""
    client = genai.Client(api_key=get_api_key())
    system_prompt = BASE_SYSTEM_PROMPT

    if args.get("context"):
        music_context = load_music_context(args["context"])
        if music_context:
            system_prompt += music_context

    text, meta = analyze_single(
        client, args["file"], args["mode"], args["model"],
        system_prompt, args.get("show_prompt", False)
    )

    # Build output with metadata header
    header = (
        f"# Recording Analysis: {meta['file']}\n"
        f"- Date: {datetime.date.today()}\n"
        f"- File: {Path(meta['file_path']).name}\n"
        f"- Mode: {meta['mode']}\n"
        f"- Model: {meta['model']}\n"
        f"- Tokens: {meta['tokens']}\n"
        f"- Analysis time: {meta['total_time_s']}s\n\n"
    )

    full_output = header + text

    # Print to stdout
    print(full_output)

    # Output metadata as JSON to stderr for SKILL.md to capture
    print(json.dumps(meta), file=sys.stderr)


def run_batch(args):
    """Run batch analysis on a directory."""
    directory = args["file"]
    files = sorted([
        f for f in Path(directory).iterdir()
        if f.suffix.lower() in SUPPORTED_EXTS
    ])

    if not files:
        print(f"ERROR: No audio files found in {directory}")
        print(f"Supported formats: {', '.join(sorted(SUPPORTED_EXTS))}")
        sys.exit(1)

    client = genai.Client(api_key=get_api_key())
    system_prompt = BASE_SYSTEM_PROMPT

    if args.get("context"):
        music_context = load_music_context(args["context"])
        if music_context:
            system_prompt += music_context

    results = []
    total_tokens = 0

    print(f"Analyzing {len(files)} recordings...")
    print("=" * 60)

    for i, f in enumerate(files, 1):
        name = f.stem
        size = f.stat().st_size / (1024 * 1024)
        print(f"[{i}/{len(files)}] {name} ({size:.1f}MB)...", end=" ", flush=True)

        try:
            text, meta = analyze_single(
                client, str(f), "json", args["model"], system_prompt
            )
            total_tokens += meta["tokens"]

            # Parse JSON
            clean = text.strip()
            if clean.startswith("```"):
                clean = clean.split("\n", 1)[1].rsplit("```", 1)[0].strip()
            try:
                data = json.loads(clean)
                data["_file"] = name
                data["_tokens"] = meta["tokens"]
                results.append(data)
                level = data.get("playing_level", "?")
                print(f"OK ({meta['total_time_s']}s, {meta['tokens']} tok) - {level}")
            except json.JSONDecodeError:
                results.append({"_file": name, "_raw": clean, "_tokens": meta["tokens"]})
                print(f"OK ({meta['total_time_s']}s) - JSON parse failed, raw saved")
        except Exception as e:
            print(f"FAILED: {e}")

    print("=" * 60)
    print(f"Analyzed {len(results)}/{len(files)} files | Total tokens: {total_tokens}")

    # Save individual results
    out_dir = Path(directory) / "analyses"
    out_dir.mkdir(exist_ok=True)

    results_path = out_dir / "batch_results.json"
    with open(results_path, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2)

    # Run synthesis
    print()
    print("Running cross-recording synthesis...")
    analyses_text = "\n\n".join([
        f"### {r.get('_file', 'Unknown')}\n"
        + json.dumps({k: v for k, v in r.items() if not k.startswith("_")}, indent=2)
        for r in results if "_raw" not in r
    ])

    synth_prompt = SYNTHESIS_PROMPT.format(count=len(results), analyses=analyses_text)

    response = client.models.generate_content(
        model=args["model"],
        config=types.GenerateContentConfig(
            system_instruction=system_prompt,
            temperature=0.3,
        ),
        contents=[synth_prompt],
    )

    synth_tokens = response.usage_metadata.total_token_count
    _log_gemini_usage(args["model"], response.usage_metadata, context="batch_synthesis")
    total_tokens += synth_tokens

    print("=" * 60)
    print(response.text)
    print("=" * 60)

    # Save synthesis
    today = datetime.date.today()
    synth_path = out_dir / f"synthesis_{today}.md"
    with open(synth_path, "w", encoding="utf-8") as f:
        f.write("# Guitar Playing Synthesis\n")
        f.write(f"- Date: {today}\n")
        f.write(f"- Recordings analyzed: {len(results)}\n")
        f.write(f"- Total tokens: {total_tokens}\n\n")
        f.write(response.text)

    # Output batch metadata to stderr
    batch_meta = {
        "mode": "batch",
        "files_analyzed": len(results),
        "files_total": len(files),
        "total_tokens": total_tokens,
        "synthesis_tokens": synth_tokens,
        "results_path": str(results_path),
        "synthesis_path": str(synth_path),
        "timestamp": datetime.datetime.now().isoformat(),
        "model": args["model"],
    }
    print(json.dumps(batch_meta), file=sys.stderr)


def parse_args():
    """Parse command-line arguments."""
    if len(sys.argv) < 2 or "--help" in sys.argv:
        print(__doc__)
        sys.exit(0)

    args = {
        "file": None,
        "mode": "solo",
        "model": DEFAULT_MODEL,
        "context": None,
        "show_prompt": False,
    }

    i = 1
    while i < len(sys.argv):
        arg = sys.argv[i]
        if arg == "--solo":
            args["mode"] = "solo"
        elif arg == "--band":
            args["mode"] = "band"
        elif arg == "--batch":
            args["mode"] = "batch"
        elif arg == "--json":
            args["mode"] = "json"
        elif arg == "--show-prompt":
            args["show_prompt"] = True
        elif arg == "--model" and i + 1 < len(sys.argv):
            i += 1
            args["model"] = sys.argv[i]
        elif arg == "--context" and i + 1 < len(sys.argv):
            i += 1
            args["context"] = sys.argv[i]
        elif not arg.startswith("--"):
            args["file"] = arg
        else:
            print(f"Unknown option: {arg}")
            print("Run with --help for usage.")
            sys.exit(1)
        i += 1

    if not args["file"]:
        print("ERROR: No file or directory specified.")
        print("Run with --help for usage.")
        sys.exit(1)

    # Validate file/directory exists
    if not os.path.exists(args["file"]):
        print(f"ERROR: Path not found: {args['file']}")
        sys.exit(1)

    # Validate format for single file mode
    if args["mode"] != "batch" and os.path.isfile(args["file"]):
        ext = Path(args["file"]).suffix.lower()
        if ext not in SUPPORTED_EXTS:
            print(f"ERROR: Unsupported format '{ext}'.")
            print(f"Supported: {', '.join(sorted(SUPPORTED_EXTS))}")
            sys.exit(1)

    # If path is a directory, force batch mode
    if os.path.isdir(args["file"]):
        args["mode"] = "batch"

    return args


def main():
    args = parse_args()

    if args["mode"] == "batch":
        run_batch(args)
    else:
        run_single(args)


if __name__ == "__main__":
    main()
