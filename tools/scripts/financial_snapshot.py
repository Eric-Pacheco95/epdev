#!/usr/bin/env python3
"""Tier-0 financial snapshot — append one JSONL row for morning briefing / G1.

Reads optional sidecar files (never invokes trading APIs). Output:
  data/financial/snapshot.jsonl  (gitignored via data/)

Env:
  CRYPTO_BOT_ROOT   -- default C:/Users/ericp/Github/crypto-bot
  CRYPTO_BOT_FINANCIAL_FILES -- optional os.pathsep-separated list of JSON files to merge
  SUBSTACK_REVENUE_PATH -- optional path to JSON with revenue fields

Autonomous Read on data/financial/* is blocked in validate_tool_use.py.
"""
from __future__ import annotations

import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT_DIR = ROOT / "data" / "financial"
OUT_FILE = OUT_DIR / "snapshot.jsonl"

_DEFAULT_BOT = Path(os.environ.get("CRYPTO_BOT_ROOT", r"C:\Users\ericp\Github\crypto-bot"))

_DEFAULT_CRYPTO_FILES = [
    "data/portfolio_snapshot.json",
    "data/paper_pnl.json",
    "data/pnl_summary.json",
    "data/account_snapshot.json",
]


def _read_json_if_exists(p: Path, max_bytes: int = 65536) -> dict | None:
    if not p.is_file():
        return None
    try:
        raw = p.read_bytes()[:max_bytes]
        return json.loads(raw.decode("utf-8", errors="replace"))
    except (OSError, json.JSONDecodeError, UnicodeError):
        return None


def _collect_crypto_payload() -> dict:
    root = Path(os.environ.get("CRYPTO_BOT_ROOT", str(_DEFAULT_BOT))).expanduser()
    extra = os.environ.get("CRYPTO_BOT_FINANCIAL_FILES", "").strip()
    paths: list[Path] = []
    if extra:
        paths.extend(Path(x.strip()) for x in extra.split(os.pathsep) if x.strip())
    else:
        for rel in _DEFAULT_CRYPTO_FILES:
            paths.append(root / rel)
    out: dict = {"root": str(root), "root_exists": root.is_dir(), "files": {}}
    for p in paths:
        key = str(p)
        loaded = _read_json_if_exists(p)
        if loaded is not None:
            out["files"][key] = loaded
    return out


def _collect_substack() -> dict | None:
    sp = os.environ.get("SUBSTACK_REVENUE_PATH", "").strip()
    if not sp:
        return None
    p = Path(sp).expanduser()
    data = _read_json_if_exists(p)
    if data is None:
        return {"path": str(p), "error": "missing_or_invalid_json"}
    return {"path": str(p), "payload": data}


def run() -> dict:
    row = {
        "ts": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "crypto_bot": _collect_crypto_payload(),
        "substack": _collect_substack(),
    }
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    with open(OUT_FILE, "a", encoding="utf-8") as f:
        f.write(json.dumps(row, ensure_ascii=False) + "\n")
    return row


def main() -> int:
    row = run()
    print(json.dumps(row, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
