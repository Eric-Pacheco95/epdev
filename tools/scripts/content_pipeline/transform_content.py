#!/usr/bin/env python3
"""transform_content.py -- Transform collected sources into a Substack draft post.

Reads staging/weekly_sources.json, builds a prompt, calls claude -p,
and writes a draft markdown file to staging/draft_YYYYMMDD.md.

Exit codes:
    0 -- draft written successfully
    1 -- error (not enough sources, rate limit, subprocess failure, I/O error)
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
STAGING = Path(__file__).resolve().parent / "staging"
SOURCES_FILE = STAGING / "weekly_sources.json"

# ---------------------------------------------------------------------------
# Rate limit phrases to detect in claude -p stdout
# ---------------------------------------------------------------------------
RATE_LIMIT_PHRASES = [
    "hit your limit",
    "rate limit",
    "too many requests",
    "quota exceeded",
]

# ---------------------------------------------------------------------------
# Prompt template
# ---------------------------------------------------------------------------
SYSTEM_PERSONA = (
    "You are writing a Substack newsletter called 'Building Jarvis' for AI systems "
    "designers and technical builders. Your voice is: direct, builder-to-builder, "
    "no hype, show don't tell. The newsletter documents the real experience of "
    "building a personal AI brain in public -- what was built this week, what "
    "problems were solved, what broke, and what generalizable lessons emerged."
)

CONTENT_REQUEST = """
Based on the source material below, generate 1 draft Substack post.

Choose the angle with highest reader value:
  (a) Build-in-public narrative: what was built, what problems were solved, what steering rules were added
  (b) A generalizable framework or mental model extracted from the work (e.g., a pattern that applies beyond this specific project)

Format requirements:
- Title: short, specific, punchy (not clickbait)
- Subtitle: one sentence that tells the reader exactly what they will learn
- TL;DR: exactly 3 bullet points at the top summarizing the key takeaways
- Body: 400-600 words. Direct prose. No section headers beyond the TL;DR block.
- Closing: one sentence on what comes next or what the reader can apply immediately

Return ONLY the post content in this exact format:

TITLE: <title here>
SUBTITLE: <subtitle here>
TLDR:
- <bullet 1>
- <bullet 2>
- <bullet 3>
BODY:
<body text here>

Do not include any preamble, explanation, or text outside this format.
"""

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def load_sources() -> dict:
    """Load weekly_sources.json. Returns the parsed dict."""
    if not SOURCES_FILE.exists():
        print(
            f"[TRANSFORM] ERROR: sources file not found: {SOURCES_FILE}",
            file=sys.stderr,
        )
        sys.exit(1)
    try:
        return json.loads(SOURCES_FILE.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError) as exc:
        print(f"[TRANSFORM] ERROR: Could not read sources file: {exc}", file=sys.stderr)
        sys.exit(1)


def format_source_block(source: dict) -> str:
    """Format a single source into a readable block for the prompt."""
    source_type = source.get("type", "unknown").upper()
    date = source.get("date", "unknown")
    path = source.get("path", "")
    rating_line = f" | Rating: {source['rating']}" if "rating" in source else ""
    filename = Path(path).name if path else "unknown"

    header = f"--- SOURCE [{source_type}] {filename} | Date: {date}{rating_line} ---"
    content = source.get("content", "").strip()
    # Truncate very long sources to keep the prompt manageable
    if len(content) > 3000:
        content = content[:3000] + "\n[... truncated for length ...]"
    return f"{header}\n{content}\n"


def build_prompt(sources: list) -> str:
    """Build the full claude -p prompt."""
    source_blocks = "\n".join(format_source_block(s) for s in sources)
    return f"{SYSTEM_PERSONA}\n\n{CONTENT_REQUEST}\n\n=== SOURCE MATERIAL ===\n\n{source_blocks}"


def check_rate_limit(stdout: str) -> bool:
    """Return True if stdout contains a rate limit message."""
    lower = stdout.lower()
    return any(phrase in lower for phrase in RATE_LIMIT_PHRASES)


def parse_draft_output(raw: str) -> dict:
    """Parse claude output into title, subtitle, tldr, body components."""
    result = {"title": "", "subtitle": "", "tldr": [], "body": ""}

    lines = raw.strip().splitlines()
    mode = None
    body_lines: list = []
    tldr_lines: list = []

    for line in lines:
        if line.startswith("TITLE:"):
            result["title"] = line[len("TITLE:"):].strip()
        elif line.startswith("SUBTITLE:"):
            result["subtitle"] = line[len("SUBTITLE:"):].strip()
        elif line.strip() == "TLDR:":
            mode = "tldr"
        elif line.strip() == "BODY:":
            mode = "body"
        elif mode == "tldr" and line.strip().startswith("-"):
            tldr_lines.append(line.strip())
        elif mode == "body":
            body_lines.append(line)
        elif mode == "tldr" and line.strip() == "":
            pass  # blank line between TLDR and BODY

    result["tldr"] = tldr_lines
    result["body"] = "\n".join(body_lines).strip()
    return result


def build_frontmatter(title: str, date_str: str) -> str:
    """Build markdown frontmatter block."""
    return f"---\ntitle: {title}\ndate: {date_str}\nstatus: draft\n---\n\n"


def build_draft_markdown(parsed: dict, date_str: str) -> str:
    """Assemble the full draft markdown file content."""
    title = parsed.get("title", "Untitled Draft")
    subtitle = parsed.get("subtitle", "")
    tldr = parsed.get("tldr", [])
    body = parsed.get("body", "")

    fm = build_frontmatter(title, date_str)
    tldr_block = "\n".join(tldr)

    return (
        f"{fm}"
        f"# {title}\n\n"
        f"*{subtitle}*\n\n"
        f"**TL;DR**\n{tldr_block}\n\n"
        f"---\n\n"
        f"{body}\n"
    )


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> int:
    print("[TRANSFORM] Loading sources...")
    data = load_sources()
    sources = data.get("sources", [])

    if len(sources) < 2:
        print(
            "[TRANSFORM] Not enough source material this week. "
            "Minimum 2 sources required."
        )
        return 1

    print(f"[TRANSFORM] {len(sources)} sources loaded. Building prompt...")
    prompt = build_prompt(sources)

    print("[TRANSFORM] Calling claude -p...")
    try:
        result = subprocess.run(
            ["claude", "-p", prompt],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=120,
        )
    except FileNotFoundError:
        print(
            "[TRANSFORM] ERROR: 'claude' command not found. "
            "Ensure claude CLI is installed and on PATH.",
            file=sys.stderr,
        )
        return 1
    except subprocess.TimeoutExpired:
        print("[TRANSFORM] ERROR: claude -p timed out after 120 seconds.", file=sys.stderr)
        return 1

    stdout = result.stdout or ""
    stderr = result.stderr or ""

    if stderr:
        print(f"[TRANSFORM] claude stderr: {stderr[:200]}", file=sys.stderr)

    # Rate limit check (must happen before exit-code check -- rate-limited runs
    # may return exit code 0 with zero real output)
    if check_rate_limit(stdout):
        print(
            "[TRANSFORM] ERROR: Rate limit hit -- run tomorrow",
            file=sys.stderr,
        )
        return 1

    if result.returncode != 0:
        print(
            f"[TRANSFORM] ERROR: claude -p exited with code {result.returncode}",
            file=sys.stderr,
        )
        return 1

    if not stdout.strip():
        print("[TRANSFORM] ERROR: claude -p returned empty output.", file=sys.stderr)
        return 1

    print("[TRANSFORM] Parsing draft output...")
    parsed = parse_draft_output(stdout)

    if not parsed["title"] or not parsed["body"]:
        print(
            "[TRANSFORM] WARN: Could not fully parse structured output. "
            "Writing raw output as draft body.",
        )
        # Fallback: write raw output
        parsed["title"] = "Draft -- parse error"
        parsed["body"] = stdout.strip()

    date_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    date_compact = datetime.now(timezone.utc).strftime("%Y%m%d")
    draft_filename = f"draft_{date_compact}.md"
    draft_path = STAGING / draft_filename

    markdown = build_draft_markdown(parsed, date_str)

    STAGING.mkdir(parents=True, exist_ok=True)
    try:
        draft_path.write_text(markdown, encoding="utf-8")
    except OSError as exc:
        print(f"[TRANSFORM] ERROR: Could not write draft file: {exc}", file=sys.stderr)
        return 1

    print(f"[TRANSFORM] Draft written: {draft_path}")
    print(f"[TRANSFORM] Title: {parsed.get('title', 'unknown')}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
