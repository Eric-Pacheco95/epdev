#!/usr/bin/env python3
"""verify_py_compile.py -- exit 0 if a repo-relative .py file compiles (py_compile).

Used by ISC templates (fix_lint). Stdlib only; safe for autonomous verify.
"""
from __future__ import annotations

import argparse
import py_compile
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
    ap = argparse.ArgumentParser(description="py_compile one repo-relative Python file.")
    ap.add_argument("rel_path", help="Path relative to repo root (POSIX-style ok)")
    args = ap.parse_args()
    try:
        target = _safe_target(args.rel_path.replace("\\", "/"))
    except ValueError as exc:
        print(exc, file=sys.stderr)
        return 2
    if not target.is_file():
        print(f"not a file: {target}", file=sys.stderr)
        return 1
    if target.suffix.lower() != ".py":
        print(f"not a .py file: {target}", file=sys.stderr)
        return 1
    try:
        py_compile.compile(str(target), doraise=True)
    except py_compile.PyCompileError as exc:
        print(exc, file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
