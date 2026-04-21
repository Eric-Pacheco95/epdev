#!/usr/bin/env python3
"""verify_repo_path_absent.py -- exit 0 if a repo-relative path does not exist.

Used by ISC templates (remove_dead_code). Complements test -f patterns on Unix.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]


def _safe_target(rel: str) -> Path:
    if not rel or rel.startswith(("/", "\\")):
        raise ValueError("path must be repo-relative")
    if ".." in Path(rel).parts:
        raise ValueError("path must not contain '..'")
    p = (REPO_ROOT / rel).resolve()
    if REPO_ROOT not in p.parents and p != REPO_ROOT:
        raise ValueError("path escapes repo root")
    return p


def main() -> int:
    ap = argparse.ArgumentParser(description="Exit 0 if path does not exist under repo.")
    ap.add_argument("rel_path", help="Path relative to repo root")
    args = ap.parse_args()
    try:
        target = _safe_target(args.rel_path.replace("\\", "/"))
    except ValueError as exc:
        print(exc, file=sys.stderr)
        return 2
    return 0 if not target.exists() else 1


if __name__ == "__main__":
    sys.exit(main())
