#!/usr/bin/env python3
"""transform_content.py -- Transform collected sources into a Substack draft post.

Reads staging/weekly_sources.json, calls the Anthropic SDK directly,
and writes a draft markdown file to staging/draft_YYYYMMDD.md.

Exit codes:
    0 -- draft written successfully
    1 -- error (not enough sources, API error, I/O error)
"""

from __future__ import annotations

import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
STAGING = Path(__file__).resolve().parent / "staging"
SOURCES_FILE = STAGING / "weekly_sources.json"

MODEL = "claude-opus-4-6"

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


def build_user_prompt(sources: list) -> str:
    """Build the user-turn prompt containing source material."""
    source_blocks = "\n".join(format_source_block(s) for s in sources)
    return f"{CONTENT_REQUEST}\n\n=== SOURCE MATERIAL ===\n\n{source_blocks}"


def call_api(user_prompt: str) -> str:
    """Call the Anthropic SDK and return the raw text response."""
    try:
        import anthropic
    except ImportError:
        print(
            "[TRANSFORM] ERROR: 'anthropic' package not installed. "
            "Run: pip install anthropic",
            file=sys.stderr,
        )
        sys.exit(1)

    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        print(
            "[TRANSFORM] ERROR: ANTHROPIC_API_KEY environment variable not set.",
            file=sys.stderr,
        )
        sys.exit(1)

    client = anthropic.Anthropic(api_key=api_key)
    message = client.messages.create(
        model=MODEL,
        max_tokens=2048,
        system=SYSTEM_PERSONA,
        messages=[{"role": "user", "content": user_prompt}],
    )
    return message.content[0].text


def parse_draft_output(raw: str) -> dict:
    """Parse API output into title, subtitle, tldr, body components."""
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
    user_prompt = build_user_prompt(sources)

    print(f"[TRANSFORM] Calling Anthropic API ({MODEL})...")
    try:
        raw_output = call_api(user_prompt)
    except Exception as exc:
        print(f"[TRANSFORM] ERROR: API call failed: {exc}", file=sys.stderr)
        return 1

    if not raw_output.strip():
        print("[TRANSFORM] ERROR: API returned empty output.", file=sys.stderr)
        return 1

    print("[TRANSFORM] Parsing draft output...")
    parsed = parse_draft_output(raw_output)

    if not parsed["title"] or not parsed["body"]:
        print(
            "[TRANSFORM] WARN: Could not fully parse structured output. "
            "Writing raw output as draft body.",
        )
        parsed["title"] = "Draft -- parse error"
        parsed["body"] = raw_output.strip()

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
