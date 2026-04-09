"""
Firecrawl MCP Smoke Test
Tests Firecrawl API against 6 representative URL types from the /research waterfall.
Results feed into /create-prd for the Firecrawl integration decision.

Usage:
    Set FIRECRAWL_API_KEY in your environment, then:
    python tools/scripts/firecrawl_smoke_test.py

Requirements:
    pip install requests
"""

import os
import sys
import json
import time
import textwrap
import requests

API_KEY = os.environ.get("FIRECRAWL_API_KEY", "")
API_BASE = "https://api.firecrawl.dev/v1"

# Representative URLs across the /research waterfall's failure modes and success cases
TEST_URLS = [
    {
        "id": "reddit_thread",
        "label": "Reddit thread (primary claimed benefit)",
        "url": "https://www.reddit.com/r/LocalLLaMA/comments/1hqy1yz/what_are_you_currently_using_claude_code_for/",
        "expected": "PASS",
        "why": "Core claimed benefit -- if this fails, the Reddit gap is not solvable by Firecrawl",
    },
    {
        "id": "reddit_subreddit",
        "label": "Reddit subreddit listing (harder target)",
        "url": "https://www.reddit.com/r/ClaudeAI/",
        "expected": "UNCERTAIN",
        "why": "Subreddit listings are more aggressively gated than single threads",
    },
    {
        "id": "js_spa",
        "label": "JS-rendered SPA (React, no SSR)",
        "url": "https://linear.app/changelog",
        "expected": "PASS",
        "why": "Pure React SPA -- WebFetch returns empty shell; Firecrawl should handle this",
    },
    {
        "id": "static_blog",
        "label": "Static blog post (control -- should work trivially)",
        "url": "https://simonwillison.net/2025/Mar/11/using-llms-for-code/",
        "expected": "PASS",
        "why": "Control case -- WebFetch already handles this; validates Firecrawl baseline",
    },
    {
        "id": "medium_article",
        "label": "Medium article (paywalled)",
        "url": "https://medium.com/towards-data-science/mcp-vs-cli-for-ai-agents-8f3e2b1a4c92",
        "expected": "UNCERTAIN",
        "why": "Medium soft-paywalls -- tests if Firecrawl bypasses or respects the paywall",
    },
    {
        "id": "linkedin_post",
        "label": "LinkedIn post (auth-gated -- current hard domain)",
        "url": "https://www.linkedin.com/pulse/mcp-vs-cli-ai-agents-andrej-karpathy/",
        "expected": "FAIL",
        "why": "Auth-gated -- tests whether Firecrawl does better than tavily_extract here",
    },
]

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


def call_firecrawl_scrape(url: str, timeout: int = 30) -> dict:
    """Call Firecrawl /scrape endpoint with markdown output."""
    headers = {
        "Authorization": f"Bearer {API_KEY}",
        "Content-Type": "application/json",
    }
    payload = {
        "url": url,
        "formats": ["markdown"],
        "onlyMainContent": True,
        "timeout": timeout * 1000,
    }
    try:
        resp = requests.post(f"{API_BASE}/scrape", headers=headers, json=payload, timeout=timeout + 5)
        return {"status_code": resp.status_code, "data": resp.json() if resp.ok else {}, "error": None if resp.ok else resp.text}
    except requests.exceptions.Timeout:
        return {"status_code": 0, "data": {}, "error": "TIMEOUT"}
    except Exception as e:
        return {"status_code": 0, "data": {}, "error": str(e)}


def check_injection(content: str) -> list[str]:
    """Check for obvious injection patterns in extracted content."""
    hits = []
    content_lower = content.lower()
    for pattern in INJECTION_SUBSTRINGS:
        if pattern in content_lower:
            hits.append(pattern)
    return hits


def grade_result(result: dict, test: dict) -> dict:
    """Grade a single test result."""
    data = result.get("data", {})
    error = result.get("error")
    status_code = result.get("status_code", 0)

    # Extract markdown content
    content = ""
    if data.get("success"):
        md = data.get("data", {})
        content = md.get("markdown", "") or ""

    content_len = len(content)
    preview = content[:300].replace("\n", " ") if content else ""
    injection_hits = check_injection(content)

    # Grade
    if error or status_code not in (200,):
        grade = "FAIL"
        reason = error or f"HTTP {status_code}"
    elif content_len < 100:
        grade = "FAIL"
        reason = f"Content too short ({content_len} chars) -- likely blocked or empty"
    elif content_len < 500:
        grade = "PARTIAL"
        reason = f"Sparse content ({content_len} chars) -- possible bot detection or paywall"
    else:
        grade = "PASS"
        reason = f"{content_len} chars extracted"

    return {
        "id": test["id"],
        "label": test["label"],
        "url": test["url"],
        "expected": test["expected"],
        "grade": grade,
        "reason": reason,
        "content_len": content_len,
        "preview": preview,
        "injection_hits": injection_hits,
        "why": test["why"],
    }


def print_row(label: str, value: str, width: int = 72) -> None:
    print(f"  {label:<20} {value[:width]}")


def main() -> None:
    if not API_KEY:
        print("ERROR: FIRECRAWL_API_KEY not set in environment.")
        print("  Get a free key at https://firecrawl.dev")
        print("  Then: set FIRECRAWL_API_KEY=fc-your-key-here")
        sys.exit(1)

    print("=" * 72)
    print("  Firecrawl MCP Smoke Test")
    print("  Testing 6 URL types from the /research extraction waterfall")
    print("=" * 72)
    print()

    results = []
    for i, test in enumerate(TEST_URLS, 1):
        print(f"[{i}/{len(TEST_URLS)}] {test['label']}")
        print(f"        {test['url']}")
        start = time.time()
        raw = call_firecrawl_scrape(test["url"])
        elapsed = time.time() - start
        graded = grade_result(raw, test)
        graded["elapsed_s"] = round(elapsed, 2)
        results.append(graded)

        status_icon = {"PASS": "[PASS]", "PARTIAL": "[PARTIAL]", "FAIL": "[FAIL]"}[graded["grade"]]
        print(f"        {status_icon}  {graded['reason']}  ({elapsed:.1f}s)")
        if graded["injection_hits"]:
            print(f"        [WARN] Injection patterns detected: {graded['injection_hits']}")
        if graded["preview"]:
            # ASCII-safe preview -- strip non-ASCII chars (Windows cp1252 safety)
            safe_preview = graded["preview"].encode("ascii", errors="replace").decode("ascii")
            wrapped = textwrap.fill(safe_preview, width=65, initial_indent="        > ", subsequent_indent="          ")
            print(wrapped)
        print()

    # Summary
    print("=" * 72)
    print("  SUMMARY")
    print("=" * 72)
    passes = [r for r in results if r["grade"] == "PASS"]
    partials = [r for r in results if r["grade"] == "PARTIAL"]
    fails = [r for r in results if r["grade"] == "FAIL"]
    injections = [r for r in results if r["injection_hits"]]

    print(f"  PASS:    {len(passes)}/{len(results)}")
    print(f"  PARTIAL: {len(partials)}/{len(results)}")
    print(f"  FAIL:    {len(fails)}/{len(results)}")
    if injections:
        print(f"  [WARN] Injection patterns detected in {len(injections)} result(s):")
        for r in injections:
            print(f"    - {r['label']}: {r['injection_hits']}")

    print()
    print("  KEY QUESTION: Does Reddit work?")
    reddit_thread = next((r for r in results if r["id"] == "reddit_thread"), None)
    reddit_sub = next((r for r in results if r["id"] == "reddit_subreddit"), None)
    if reddit_thread:
        icon = "[PASS]" if reddit_thread["grade"] == "PASS" else "[FAIL]"
        print(f"    Reddit thread:    {icon}  {reddit_thread['reason']}")
    if reddit_sub:
        icon = "[PASS]" if reddit_sub["grade"] == "PASS" else "[FAIL]"
        print(f"    Reddit subreddit: {icon}  {reddit_sub['reason']}")

    js_spa = next((r for r in results if r["id"] == "js_spa"), None)
    if js_spa:
        print()
        print("  KEY QUESTION: Does JS rendering work (beyond what WebFetch handles)?")
        icon = "[PASS]" if js_spa["grade"] == "PASS" else "[FAIL]"
        print(f"    JS SPA:  {icon}  {js_spa['reason']}")

    # PRD input verdict
    print()
    print("  PRD ADOPTION VERDICT")
    print("  --------------------")
    reddit_pass = reddit_thread and reddit_thread["grade"] == "PASS"
    spa_pass = js_spa and js_spa["grade"] == "PASS"

    if reddit_pass and spa_pass:
        verdict = "ADOPT -- core benefits validated. Build with MCP + sanitization layer."
    elif spa_pass and not reddit_pass:
        verdict = "ADOPT (scoped) -- JS rendering validated; Reddit gap persists. Update waterfall doc to reflect Reddit still manual-paste."
    elif reddit_pass and not spa_pass:
        verdict = "INVESTIGATE -- Reddit works but JS SPA failed unexpectedly. Retest."
    else:
        verdict = "REJECT -- neither primary benefit validated. Do not proceed with adoption."

    print(f"  {verdict}")
    print()

    # Write JSON results for /create-prd input
    output_path = "memory/work/firecrawl_smoke_results.json"
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(
            {
                "test_date": time.strftime("%Y-%m-%d"),
                "api_version": "v1",
                "integration_target": "Firecrawl MCP (not CLI)",
                "verdict": verdict,
                "pass_count": len(passes),
                "partial_count": len(partials),
                "fail_count": len(fails),
                "injection_warnings": len(injections),
                "results": results,
            },
            f,
            indent=2,
            ensure_ascii=True,
        )
    print(f"  Full results written to {output_path}")
    print("  Feed this file into /create-prd for the Firecrawl integration PRD.")
    print("=" * 72)


if __name__ == "__main__":
    main()
