"""
Secret pattern detection for commands and file contents (stdlib only).
Patterns align with security/constitutional-rules.md.
"""

from __future__ import annotations

import fnmatch
import re
from pathlib import Path
from typing import Iterable


# Named patterns for tests and reporting
SECRET_PATTERNS: tuple[tuple[str, re.Pattern[str]], ...] = (
    ("sk-", re.compile(r"\bsk-[a-zA-Z0-9]{10,}", re.IGNORECASE)),
    ("AKIA", re.compile(r"AKIA[0-9A-Z]{16}")),
    ("ghp_", re.compile(r"ghp_[a-zA-Z0-9]{20,}")),
    ("xoxb-", re.compile(r"xoxb-[0-9]+-[0-9]+-[a-zA-Z0-9]+")),
    ("-----BEGIN", re.compile(r"-----BEGIN [A-Z0-9 ]+-----")),
)


def line_has_secret(line: str) -> tuple[bool, str | None]:
    """Return (found, pattern_name)."""
    for name, rx in SECRET_PATTERNS:
        if rx.search(line):
            return True, name
    return False, None


def scan_text(text: str) -> list[tuple[int, str, str]]:
    """Return list of (line_number_1_based, pattern_name, line_snippet)."""
    hits: list[tuple[int, str, str]] = []
    for i, line in enumerate(text.splitlines(), start=1):
        found, name = line_has_secret(line)
        if found and name:
            snippet = line.strip()[:200]
            hits.append((i, name, snippet))
    return hits


def scan_file(path: Path) -> list[tuple[int, str, str]]:
    raw = path.read_bytes()
    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError:
        text = raw.decode("utf-8", errors="replace")
    return scan_text(text)


def _parse_gitignore_lines(content: str) -> list[str]:
    rules: list[str] = []
    for line in content.splitlines():
        s = line.strip()
        if not s or s.startswith("#"):
            continue
        if s.startswith("!"):
            continue
        rules.append(s.rstrip("/"))
    return rules


def load_gitignore_patterns(gitignore_path: Path) -> list[str]:
    if not gitignore_path.is_file():
        return []
    return _parse_gitignore_lines(gitignore_path.read_text(encoding="utf-8", errors="replace"))


def path_matches_gitignore(relative_posix: str, patterns: Iterable[str]) -> bool:
    """Basic gitignore-style matching (fnmatch). relative_posix uses forward slashes."""
    rel = relative_posix.lstrip("./")
    for pat in patterns:
        if "/" in pat:
            if fnmatch.fnmatch(rel, pat) or fnmatch.fnmatch(rel, pat + "/**"):
                return True
        else:
            if fnmatch.fnmatch(Path(rel).name, pat) or fnmatch.fnmatch(rel, pat):
                return True
            parts = rel.split("/")
            for part in parts:
                if fnmatch.fnmatch(part, pat):
                    return True
    return False


def iter_scannable_files(
    root: Path,
    gitignore_patterns: list[str],
) -> Iterable[Path]:
    """Yield files under root that are not ignored by patterns."""
    root = root.resolve()
    for p in root.rglob("*"):
        if not p.is_file():
            continue
        try:
            rel = p.relative_to(root).as_posix()
        except ValueError:
            continue
        if p.name == ".gitignore":
            continue
        if path_matches_gitignore(rel, gitignore_patterns):
            continue
        yield p


def scan_tree(
    root: Path,
    gitignore_path: Path | None = None,
) -> dict[str, list[tuple[int, str, str]]]:
    """
    Scan all non-ignored files under root for secret patterns.
    Returns map path_str -> list of hits.
    """
    patterns = load_gitignore_patterns(gitignore_path) if gitignore_path else []
    results: dict[str, list[tuple[int, str, str]]] = {}
    for f in iter_scannable_files(root, patterns):
        hits = scan_file(f)
        if hits:
            results[str(f)] = hits
    return results
