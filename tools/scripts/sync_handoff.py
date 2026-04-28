#!/usr/bin/env python3
"""Sync handoff state to git reality.

Reads a session handoff file, extracts ## Pending Efforts entries, and runs
deterministic git checks to surface candidate commits that may already have
shipped each effort. Output is evidence + heuristic verdict; the human still
decides what's actually done.

Heuristics per effort:
  - Extract file paths from the effort body (regex on tokens with extensions).
  - Extract title keywords (skip stopwords).
  - Query A: `git log --since=<mtime> -- <path>` for each extracted path.
  - Query B: `git log --since=<mtime> --grep=<keyword>` for each title keyword.
  - Verdict: DONE if any commit hits both A and B; LIKELY-DONE if A only;
    KEYWORD-HIT if B only; PENDING if neither.

Usage:
    python tools/scripts/sync_handoff.py                      # newest handoff
    python tools/scripts/sync_handoff.py path/to/handoff.md
    python tools/scripts/sync_handoff.py --json
    python tools/scripts/sync_handoff.py --self-test

The handoff file's mtime is the cutoff -- commits older than that are not
considered. This means handoffs that are edited after their nominal write
time will shift the window; that's by design (mtime = "this is the freshest
intent").
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

# Backdate the cutoff this many hours from the handoff mtime. The point of
# /sync-handoff is to catch the staleness pattern where a handoff is *written*
# after the work it claims is pending; using mtime as a hard cutoff would
# filter out exactly those commits. 48h covers same-day-thread overlap and
# leaves enough headroom for late-night handoff edits.
LOOKBACK_HOURS = 48

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
HANDOFF_DIR = REPO_ROOT / "data"

# Common file extensions worth grepping for in handoff bodies.
PATH_RE = re.compile(r"[\w./-]+\.(?:md|py|json|js|ts|tsx|sh|yaml|yml|toml)\b")

# 7-40 hex chars, surrounded by word boundaries -- matches commit shorthashes.
COMMIT_RE = re.compile(r"\b([0-9a-f]{7,40})\b")

STOPWORDS = {
    "the", "a", "an", "and", "or", "to", "of", "in", "on", "at", "for",
    "with", "by", "as", "is", "it", "be", "this", "that", "from", "into",
    "rule", "add", "audit", "patch", "fix", "via", "vs", "not", "min",
    "max", "new", "old", "ready", "done", "pending", "kickoff", "source",
    "signal", "prior", "next", "skill", "skills", "before", "after",
    "session", "task", "step", "steps", "see", "ref", "etc", "todo",
}


def run_git(args: list[str]) -> str:
    """Run git, return stdout. Empty string on failure (caller decides)."""
    try:
        out = subprocess.run(
            ["git", *args],
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            check=False,
        )
    except FileNotFoundError:
        return ""
    return out.stdout if out.returncode == 0 else ""


def newest_handoff() -> Path | None:
    candidates = sorted(
        HANDOFF_DIR.glob("session_handoff_*.md"),
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )
    return candidates[0] if candidates else None


def parse_pending(text: str) -> list[dict]:
    """Split out each `### ...` effort under `## Pending Efforts`."""
    m = re.search(r"^##\s+Pending\s+Efforts\s*$", text, flags=re.MULTILINE | re.IGNORECASE)
    if not m:
        return []
    section = text[m.end():]
    next_h2 = re.search(r"^##\s+", section, flags=re.MULTILINE)
    if next_h2:
        section = section[:next_h2.start()]

    efforts = []
    parts = re.split(r"^###\s+(.+?)$", section, flags=re.MULTILINE)
    # parts = [pre-section-noise, title1, body1, title2, body2, ...]
    for i in range(1, len(parts), 2):
        title = parts[i].strip()
        body = parts[i + 1] if i + 1 < len(parts) else ""
        efforts.append({"title": title, "body": body})
    return efforts


def extract_paths(text: str) -> list[str]:
    """Return file paths mentioned in the body that exist in the working tree."""
    seen: set[str] = set()
    out: list[str] = []
    for m in PATH_RE.finditer(text):
        p = m.group(0).strip("./")
        if p in seen:
            continue
        seen.add(p)
        # Resolve against repo root; only return if file exists.
        if (REPO_ROOT / p).exists():
            out.append(p)
    return out


def extract_keywords(title: str) -> list[str]:
    """Pull non-stopword tokens from the effort title for grep queries."""
    tokens = re.findall(r"[A-Za-z][A-Za-z0-9\-_]{2,}", title)
    out = []
    for t in tokens:
        low = t.lower()
        if low in STOPWORDS:
            continue
        out.append(t)
    return out


def commits_touching(path: str, since_iso: str) -> list[tuple[str, str]]:
    raw = run_git(["log", f"--since={since_iso}", "--pretty=%h %s", "--", path])
    return [tuple(line.split(" ", 1)) for line in raw.splitlines() if " " in line]


def commits_grepping(keyword: str, since_iso: str) -> list[tuple[str, str]]:
    raw = run_git(["log", f"--since={since_iso}", f"--grep={keyword}", "-i", "--pretty=%h %s"])
    return [tuple(line.split(" ", 1)) for line in raw.splitlines() if " " in line]


def classify(path_hits: dict, keyword_hits: dict) -> str:
    """Path hits drive the verdict; keyword hits are supplementary evidence
    only -- short keywords like 'TDD' generate false positives via -i grep,
    and we don't want those flipping a verdict."""
    path_commits = {h for hits in path_hits.values() for h, _ in hits}
    keyword_commits = {h for hits in keyword_hits.values() for h, _ in hits}
    if path_commits:
        return "DONE" if (path_commits & keyword_commits) else "LIKELY-DONE"
    return "KEYWORD-HIT" if keyword_commits else "PENDING"


def audit(handoff_path: Path) -> dict:
    text = handoff_path.read_text(encoding="utf-8")
    mtime = datetime.fromtimestamp(handoff_path.stat().st_mtime, tz=timezone.utc)
    cutoff = mtime - timedelta(hours=LOOKBACK_HOURS)
    since_iso = cutoff.isoformat()

    efforts = parse_pending(text)
    results = []

    for eff in efforts:
        body = eff["body"]
        paths = extract_paths(body)
        # Limit keywords to the 5 most distinctive (longest first).
        keywords = sorted(extract_keywords(eff["title"]), key=len, reverse=True)[:5]
        commits_in_handoff = COMMIT_RE.findall(body)

        path_hits = {p: commits_touching(p, since_iso) for p in paths}
        keyword_hits = {k: commits_grepping(k, since_iso) for k in keywords}

        verdict = classify(path_hits, keyword_hits)

        path_commits = {h: msg for hits in path_hits.values() for h, msg in hits}
        # Only keyword hits from distinctive (>=8 char) keywords are worth
        # showing -- short keywords like "TDD" generate too many false hits.
        distinctive_kw_hits: dict[str, str] = {}
        for kw, hits in keyword_hits.items():
            if len(kw) >= 8:
                for h, msg in hits:
                    distinctive_kw_hits.setdefault(h, msg)
        # When verdict is DONE (path + keyword overlap), we already have high
        # confidence -- suppress keyword-only display. Otherwise show.
        if verdict == "DONE":
            keyword_only = {}
        else:
            keyword_only = {h: msg for h, msg in distinctive_kw_hits.items() if h not in path_commits}

        results.append({
            "title": eff["title"],
            "paths": paths,
            "keywords": keywords,
            "referenced_commits": commits_in_handoff,
            "verdict": verdict,
            "path_commits": [{"hash": h, "subject": msg} for h, msg in path_commits.items()],
            "keyword_only_commits": [{"hash": h, "subject": msg} for h, msg in keyword_only.items()],
        })

    return {
        "handoff": str(handoff_path.relative_to(REPO_ROOT)),
        "handoff_mtime": mtime.isoformat(),
        "cutoff": since_iso,
        "lookback_hours": LOOKBACK_HOURS,
        "effort_count": len(efforts),
        "efforts": results,
    }


def render(state: dict) -> str:
    if state["effort_count"] == 0:
        return f"{state['handoff']} (mtime {state['handoff_mtime']})\n  no '## Pending Efforts' section found, or section is empty"

    lines = [
        f"Handoff: {state['handoff']} (mtime {state['handoff_mtime']})",
        f"Cutoff:  {state['cutoff']} (handoff mtime - {state['lookback_hours']}h)",
        f"Found {state['effort_count']} effort(s):",
        "",
    ]
    for eff in state["efforts"]:
        lines.append(f"### {eff['title']}")
        lines.append(f"  Verdict: {eff['verdict']}")
        if eff["paths"]:
            lines.append(f"  Paths:   {', '.join(eff['paths'])}")
        if eff["keywords"]:
            lines.append(f"  Keywords: {', '.join(eff['keywords'])}")
        if eff["path_commits"]:
            lines.append("  Path-touching commits:")
            for c in eff["path_commits"]:
                lines.append(f"    {c['hash']} {c['subject']}")
        if eff["keyword_only_commits"]:
            lines.append("  Keyword-only candidate commits (no path overlap):")
            for c in eff["keyword_only_commits"][:5]:
                lines.append(f"    {c['hash']} {c['subject']}")
            if len(eff["keyword_only_commits"]) > 5:
                lines.append(f"    ... and {len(eff['keyword_only_commits']) - 5} more")
        if not eff["path_commits"] and not eff["keyword_only_commits"]:
            lines.append("  No candidate commits in window.")
        lines.append("")
    return "\n".join(lines).rstrip()


def _self_test() -> int:
    sample = (
        "# Handoff\n\n## Done This Session\n- thing\n\n"
        "## Pending Efforts\n\n"
        "### #2 — TDD rule\n**State:** ready\n`orchestration/steering/testing-governance.md`\n\n"
        "### #4 — frontmatter audit\nuses `disable-model-invocation`\n\n"
        "## Quick Start\nrun #2.\n"
    )
    efforts = parse_pending(sample)
    assert len(efforts) == 2, efforts
    assert efforts[0]["title"].startswith("#2"), efforts[0]
    paths = extract_paths(efforts[0]["body"])
    # The path may not exist in test env; accept either result.
    kws = extract_keywords(efforts[0]["title"])
    assert "TDD" in kws, kws
    print("self-test PASS")
    return 0


def main() -> int:
    # Windows default cp1252 stdout chokes on unicode arrows etc. that handoffs use.
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser()
    ap.add_argument("path", nargs="?", help="handoff file (default: newest in data/)")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--self-test", action="store_true")
    args = ap.parse_args()

    if args.self_test:
        return _self_test()

    if args.path:
        handoff = Path(args.path)
        if not handoff.is_absolute():
            handoff = REPO_ROOT / handoff
    else:
        handoff = newest_handoff()
        if handoff is None:
            print("no handoff files found in data/", file=sys.stderr)
            return 1

    if not handoff.exists():
        print(f"handoff not found: {handoff}", file=sys.stderr)
        return 1

    state = audit(handoff)

    if args.json:
        print(json.dumps(state, indent=2))
    else:
        print(render(state))

    return 0


if __name__ == "__main__":
    sys.exit(main())
