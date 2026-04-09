"""
Firecrawl API wrapper -- thin lib for /scrape endpoint.

Used by /research waterfall (Step 2.5) for JS SPA / paywall extraction
when tavily_extract fails or credits are exhausted. Direct requests, not MCP.

Usage:
    from tools.scripts.lib.firecrawl import scrape

    result = scrape("https://linear.app/changelog")
    if result.ok:
        print(result.markdown)
    else:
        print(f"Failed: {result.error}")

Requirements:
    - FIRECRAWL_API_KEY env var
    - pip install requests
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import Optional

import requests

API_BASE = "https://api.firecrawl.dev/v1"
DEFAULT_TIMEOUT_S = 30

# Lifted from firecrawl_smoke_test.py -- prompt-injection substrings to flag
# in extracted content. Caller decides whether to discard or downrank.
INJECTION_SUBSTRINGS = [
    "ignore previous instructions",
    "disregard your",
    "your instructions are now",
    "instead, you should",
    "system prompt",
    "forget everything",
    "new instructions:",
    "<!-- instructions",
]


@dataclass
class ScrapeResult:
    ok: bool
    url: str
    markdown: str = ""
    content_len: int = 0
    status_code: int = 0
    elapsed_s: float = 0.0
    error: Optional[str] = None
    injection_hits: list[str] = field(default_factory=list)


def _ascii_safe(text: str) -> str:
    """Strip non-ASCII so callers can print on Windows cp1252 without crashing."""
    return text.encode("ascii", errors="replace").decode("ascii")


def check_injection(content: str) -> list[str]:
    """Return any injection substrings found in content (lowercased match)."""
    if not content:
        return []
    lower = content.lower()
    return [p for p in INJECTION_SUBSTRINGS if p in lower]


def scrape(
    url: str,
    timeout_s: int = DEFAULT_TIMEOUT_S,
    only_main_content: bool = True,
    ascii_safe: bool = True,
) -> ScrapeResult:
    """
    Scrape a single URL via Firecrawl /scrape, return markdown + injection check.

    - timeout_s: HTTP timeout for the API call
    - only_main_content: strip nav/footer/sidebar (Firecrawl's onlyMainContent)
    - ascii_safe: strip non-ASCII from markdown so caller can print on Windows
    """
    import time as _time

    api_key = os.environ.get("FIRECRAWL_API_KEY", "")
    if not api_key:
        return ScrapeResult(
            ok=False,
            url=url,
            error="FIRECRAWL_API_KEY not set in environment",
        )

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    payload = {
        "url": url,
        "formats": ["markdown"],
        "onlyMainContent": only_main_content,
        "timeout": timeout_s * 1000,
    }

    start = _time.time()
    try:
        resp = requests.post(
            f"{API_BASE}/scrape",
            headers=headers,
            json=payload,
            timeout=timeout_s + 5,
        )
    except requests.exceptions.Timeout:
        return ScrapeResult(
            ok=False,
            url=url,
            elapsed_s=round(_time.time() - start, 2),
            error="TIMEOUT",
        )
    except requests.exceptions.RequestException as e:
        return ScrapeResult(
            ok=False,
            url=url,
            elapsed_s=round(_time.time() - start, 2),
            error=f"REQUEST_ERROR: {e}",
        )

    elapsed = round(_time.time() - start, 2)

    if resp.status_code != 200:
        return ScrapeResult(
            ok=False,
            url=url,
            status_code=resp.status_code,
            elapsed_s=elapsed,
            error=f"HTTP {resp.status_code}: {resp.text[:200]}",
        )

    try:
        data = resp.json()
    except ValueError as e:
        return ScrapeResult(
            ok=False,
            url=url,
            status_code=resp.status_code,
            elapsed_s=elapsed,
            error=f"JSON_DECODE: {e}",
        )

    if not data.get("success"):
        return ScrapeResult(
            ok=False,
            url=url,
            status_code=resp.status_code,
            elapsed_s=elapsed,
            error=f"API_ERROR: {data.get('error', 'unknown')}",
        )

    markdown = (data.get("data", {}).get("markdown") or "")
    if ascii_safe:
        markdown = _ascii_safe(markdown)

    return ScrapeResult(
        ok=True,
        url=url,
        markdown=markdown,
        content_len=len(markdown),
        status_code=resp.status_code,
        elapsed_s=elapsed,
        injection_hits=check_injection(markdown),
    )


if __name__ == "__main__":
    # CLI smoke: python -m tools.scripts.lib.firecrawl <url>
    import sys

    if len(sys.argv) < 2:
        print("usage: python -m tools.scripts.lib.firecrawl <url>")
        sys.exit(2)

    target = sys.argv[1]
    result = scrape(target)
    if not result.ok:
        print(f"[FAIL] {result.error}")
        sys.exit(1)
    print(f"[PASS] {result.content_len} chars in {result.elapsed_s}s")
    if result.injection_hits:
        print(f"[WARN] injection hits: {result.injection_hits}")
    print("---")
    print(result.markdown[:500])
