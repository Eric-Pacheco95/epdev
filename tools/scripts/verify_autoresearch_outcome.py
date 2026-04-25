#!/usr/bin/env python3
"""Tier 1 verifier for autoresearch skill launcher output.

Gates (all must pass for exit 0):
  (a) >=1 file in knowledge dir with >=300 words
  (b) >=3 parseable https:// URLs in file body
  (c) no orphan citations: URLs in ## Citations section also appear in body
  (d) bytes_written / tokens_spent >= threshold (informational; skipped if tokens=0)

Exit 0: all hard gates pass.
Exit 1: any gate fails; prints JSON reason to stdout.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
_CONFIG_PATH = Path(__file__).resolve().parent / "verify_autoresearch_config.json"
_URL_RE = re.compile(r"https?://[^\s\"'<>)\]]+")
_SECTION_RE = re.compile(r"^##\s+(?:citations?|references?)\s*$", re.IGNORECASE | re.MULTILINE)


def _load_config() -> dict:
    try:
        return json.loads(_CONFIG_PATH.read_text(encoding="utf-8"))
    except Exception:
        return {"min_words": 300, "min_citation_urls": 3, "bytes_per_token_min_ratio": 2.0}


def _fail(reason: str, detail: str = "") -> int:
    print(json.dumps({"exit_code": 1, "reason": reason, "detail": detail}))
    return 1


def _find_target_file(knowledge_dir: Path, since_time: datetime | None) -> Path | None:
    """Return the best candidate knowledge file: newest file passing since_time filter."""
    candidates = []
    for p in knowledge_dir.rglob("*.md"):
        if not p.is_file():
            continue
        if since_time is not None:
            mtime = datetime.fromtimestamp(p.stat().st_mtime, tz=timezone.utc)
            if mtime < since_time:
                continue
        candidates.append(p)
    if not candidates:
        return None
    return max(candidates, key=lambda p: p.stat().st_mtime)


def _split_body_and_citations(text: str) -> tuple[str, str]:
    """Return (body_text, citations_section_text) split at first ## Citations heading."""
    m = _SECTION_RE.search(text)
    if not m:
        return text, ""
    return text[: m.start()], text[m.start():]


def verify_file(path: Path, cfg: dict, tokens_spent: int) -> int:
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except OSError as exc:
        return _fail("file_read_error", str(exc))

    # Gate (a): word count
    words = len(text.split())
    if words < cfg["min_words"]:
        return _fail(
            "stub_file_rejected",
            f"{path.name}: {words} words < minimum {cfg['min_words']}",
        )

    body, citations_section = _split_body_and_citations(text)

    # Gate (b): URL count in body
    urls_in_body = _URL_RE.findall(body)
    if len(urls_in_body) < cfg["min_citation_urls"]:
        return _fail(
            "insufficient_citations",
            f"{path.name}: {len(urls_in_body)} URLs in body < minimum {cfg['min_citation_urls']}",
        )

    # Gate (c): orphan citation check
    if citations_section:
        citation_urls = _URL_RE.findall(citations_section)
        body_lower = body.lower()
        orphans = [u for u in citation_urls if u.lower() not in body_lower]
        if orphans:
            return _fail(
                "orphan_citations",
                f"{path.name}: {len(orphans)} citation URL(s) not found in body: {orphans[:3]}",
            )

    # Gate (d): token ratio (informational — skip if tokens=0)
    if tokens_spent > 0:
        ratio = len(text.encode("utf-8")) / tokens_spent
        threshold = cfg.get("bytes_per_token_min_ratio", 2.0)
        if ratio < threshold:
            print(
                json.dumps({
                    "gate_d": "informational_warning",
                    "bytes_per_token": round(ratio, 3),
                    "threshold": threshold,
                    "note": "v1 informational — not a hard exit gate",
                }),
                file=sys.stderr,
            )

    print(json.dumps({"exit_code": 0, "file": str(path), "words": words}))
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Verify autoresearch output quality")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--knowledge-dir", type=Path, help="Directory to scan for new knowledge files")
    group.add_argument("--knowledge-file", type=Path, help="Specific knowledge file to verify")
    parser.add_argument("--tokens-spent", type=int, default=0)
    parser.add_argument("--since-time", help="ISO8601 timestamp; only files newer than this count")
    args = parser.parse_args()

    cfg = _load_config()

    since_time: datetime | None = None
    if args.since_time:
        try:
            since_time = datetime.fromisoformat(args.since_time.replace("Z", "+00:00"))
        except ValueError:
            pass

    if args.knowledge_file is not None:
        target = args.knowledge_file
        if not target.is_file():
            return _fail("file_not_found", str(target))
    else:
        knowledge_dir = args.knowledge_dir
        if not knowledge_dir.is_dir():
            return _fail("knowledge_dir_not_found", str(knowledge_dir))
        target = _find_target_file(knowledge_dir, since_time)
        if target is None:
            return _fail(
                "no_new_knowledge_files",
                f"No .md files newer than {args.since_time or 'epoch'} in {knowledge_dir}",
            )

    return verify_file(target, cfg, args.tokens_spent)


if __name__ == "__main__":
    sys.exit(main())
