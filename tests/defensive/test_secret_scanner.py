#!/usr/bin/env python3
"""Defensive tests: secret scanner patterns, clean files, .gitignore."""

from __future__ import annotations

import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from security.validators.secret_scanner import (
    line_has_secret,
    load_gitignore_patterns,
    path_matches_gitignore,
    scan_file,
    scan_tree,
)


def _pass(name: str) -> None:
    print(f"PASS: {name}")


def _fail(name: str, detail: str = "") -> None:
    print(f"FAIL: {name}")
    if detail:
        print(f"      {detail}")


def main() -> None:
    ok = True

    # Pattern: sk-
    line = "key = sk-123456789012345678901234567890"
    found, name = line_has_secret(line)
    if found and name == "sk-":
        _pass("pattern sk- detected")
    else:
        ok = False
        _fail("pattern sk-", f"found={found} name={name!r}")

    # AKIA
    line = "export AWS_ACCESS_KEY_ID=AKIA1234567890ABCDEF"
    found, name = line_has_secret(line)
    if found and name == "AKIA":
        _pass("pattern AKIA detected")
    else:
        ok = False
        _fail("pattern AKIA", f"found={found} name={name!r}")

    # ghp_
    line = "token ghp_fakefakefakefakefakefakefake1234567890"
    found, name = line_has_secret(line)
    if found and name == "ghp_":
        _pass("pattern ghp_ detected")
    else:
        ok = False
        _fail("pattern ghp_", f"found={found} name={name!r}")

    # xoxb-
    line = "slack xoxb-123-456-abcdef0123456789"
    found, name = line_has_secret(line)
    if found and name == "xoxb-":
        _pass("pattern xoxb- detected")
    else:
        ok = False
        _fail("pattern xoxb-", f"found={found} name={name!r}")

    # PEM
    line = "-----BEGIN RSA PRIVATE KEY-----"
    found, name = line_has_secret(line)
    if found and name == "-----BEGIN":
        _pass("pattern -----BEGIN detected")
    else:
        ok = False
        _fail("pattern -----BEGIN", f"found={found} name={name!r}")

    # Temp tree: secrets in scanned file
    with tempfile.TemporaryDirectory() as tmp:
        base = Path(tmp)
        dirty = base / "dirty.env"
        dirty.write_text(
            "AWS_ACCESS_KEY_ID=AKIA1234567890ABCDEF\n"
            "GITHUB_TOKEN=ghp_fakefakefakefakefakefakefake1234567890\n",
            encoding="utf-8",
        )
        hits = scan_file(dirty)
        if hits:
            _pass("scan_file finds secrets in temp file")
        else:
            ok = False
            _fail("scan_file on dirty.env")

        clean = base / "clean.txt"
        clean.write_text("hello world\nno secrets here\n", encoding="utf-8")
        if not scan_file(clean):
            _pass("clean file has no hits")
        else:
            ok = False
            _fail("clean file false positive", str(scan_file(clean)))

        # .gitignore: ignore *.ignored
        gi = base / ".gitignore"
        gi.write_text("*.ignored\nbuild/\n", encoding="utf-8")
        patterns = load_gitignore_patterns(gi)
        ignored_file = base / "secrets.ignored"
        ignored_file.write_text("AKIA1234567890ABCDEF\n", encoding="utf-8")
        rel = ignored_file.relative_to(base).as_posix()
        if path_matches_gitignore(rel, patterns):
            _pass("gitignore matches *.ignored")
        else:
            ok = False
            _fail("gitignore *.ignored")

        results = scan_tree(base, gitignore_path=gi)
        if str(ignored_file) not in results:
            _pass("scan_tree respects .gitignore for ignored file")
        else:
            ok = False
            _fail("scan_tree should skip gitignored file", str(results.keys()))

        if str(dirty) in results or any("AKIA" in str(v) for v in results.values()):
            _pass("scan_tree still finds non-ignored secrets")
        else:
            ok = False
            _fail("scan_tree should see dirty.env", str(results))

    if not ok:
        sys.exit(1)
    print("All secret scanner checks passed.")


if __name__ == "__main__":
    main()
