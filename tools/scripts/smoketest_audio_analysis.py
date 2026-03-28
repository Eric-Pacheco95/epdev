"""
Smoke test: Gemini audio analysis for guitar/music recordings.
Tests whether Gemini can produce musically actionable feedback from audio files.

Usage:
    python tools/scripts/smoketest_audio_analysis.py <audio_file_path>
    python tools/scripts/smoketest_audio_analysis.py <audio_file_path> --solo
    python tools/scripts/smoketest_audio_analysis.py <audio_file_path> --band
"""

import sys
import os
import time
from pathlib import Path

# Load .env from epdev root
env_path = Path(__file__).resolve().parents[2] / ".env"
if env_path.exists():
    with open(env_path, "r") as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                key, _, value = line.partition("=")
                os.environ.setdefault(key.strip(), value.strip())

from google import genai
from google.genai import types


SYSTEM_PROMPT = """You are an expert guitar instructor and music analyst with deep knowledge of:
- Improvisational guitar styles (Jerry Garcia, John Mayer, jazz, funk, Grateful Dead tradition)
- Music theory (scales, modes, chord-scale relationships, voice leading)
- Guitar technique (phrasing, dynamics, vibrato, bending, legato, picking articulation)
- Rhythm and timing (behind/ahead of beat feel, groove, swing)
- Tone and sound design (amp tones, effects, clean vs driven)

Your job is to analyze audio recordings of guitar playing and provide SPECIFIC, ACTIONABLE feedback.
Do NOT give generic encouragement. Be honest and technical.
Reference specific musical concepts by name."""

ANALYSIS_PROMPT_SOLO = """Analyze this solo guitar recording. Provide structured feedback:

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
- Rate the playing level (beginner/intermediate/advanced/professional)
- One sentence summary of the most important thing to work on next."""

ANALYSIS_PROMPT_BAND = """Analyze this band recording, focusing specifically on the LEAD GUITAR playing.
Note: this is a full band recording -- try to focus your analysis on the guitar parts.

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
- Rate the playing level
- One sentence: most important thing to work on next."""


def main():
    if len(sys.argv) < 2:
        print("Usage: python smoketest_audio_analysis.py <audio_file> [--solo|--band]")
        print("  --solo  (default) Solo guitar or guitar-focused recording")
        print("  --band  Full band recording, analyze lead guitar")
        sys.exit(1)

    file_path = sys.argv[1]
    mode = "solo"
    if "--band" in sys.argv:
        mode = "band"

    if not os.path.exists(file_path):
        print(f"ERROR: File not found: {file_path}")
        sys.exit(1)

    file_size_mb = os.path.getsize(file_path) / (1024 * 1024)
    ext = Path(file_path).suffix.lower()
    print(f"File: {Path(file_path).name}")
    print(f"Size: {file_size_mb:.1f} MB")
    print(f"Format: {ext}")
    print(f"Mode: {mode}")
    print(f"Model: gemini-3-flash-preview")
    print("-" * 60)

    api_key = os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
    if not api_key:
        print("ERROR: No GEMINI_API_KEY or GOOGLE_API_KEY found in environment or .env")
        sys.exit(1)

    client = genai.Client(api_key=api_key)

    print("Uploading audio file to Gemini...")
    start = time.time()
    uploaded_file = client.files.upload(file=file_path)
    upload_time = time.time() - start
    print(f"Upload complete ({upload_time:.1f}s) - {uploaded_file.name}")

    # Wait for processing if needed
    while uploaded_file.state.name == "PROCESSING":
        print("  Processing...")
        time.sleep(2)
        uploaded_file = client.files.get(name=uploaded_file.name)

    if uploaded_file.state.name == "FAILED":
        print(f"ERROR: File processing failed: {uploaded_file.state}")
        sys.exit(1)

    prompt = ANALYSIS_PROMPT_SOLO if mode == "solo" else ANALYSIS_PROMPT_BAND

    print("Analyzing audio (this may take 15-30s)...")
    start = time.time()
    response = client.models.generate_content(
        model="gemini-3-flash-preview",
        config=types.GenerateContentConfig(
            system_instruction=SYSTEM_PROMPT,
            temperature=0.3,
        ),
        contents=[prompt, uploaded_file],
    )
    analysis_time = time.time() - start

    print(f"Analysis complete ({analysis_time:.1f}s)")
    print("=" * 60)
    print()
    print(response.text)
    print()
    print("=" * 60)
    print(f"Tokens used: {response.usage_metadata.total_token_count}")
    print(f"Total time: {upload_time + analysis_time:.1f}s")

    # Cleanup uploaded file
    try:
        client.files.delete(name=uploaded_file.name)
        print("Uploaded file cleaned up.")
    except Exception:
        pass


if __name__ == "__main__":
    main()
