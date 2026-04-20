#!/usr/bin/env python3
"""Append one entry to memory/learning/signals/vector-wins.jsonl.

Called by /research Phase 0.5 when Eric confirms loading a semantic hit
with score >= 0.80.

Usage:
    python tools/scripts/log_vector_win.py "<query>" "<hit_path>" <score> [source_tier]

source_tier defaults to "eric" (interactive session).
"""
import sys
import time
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT))

from tools.scripts.lib.signal_writer import append_signal  # noqa: E402

SIGNAL_PATH = REPO_ROOT / "memory" / "learning" / "signals" / "vector-wins.jsonl"


def main() -> int:
    if len(sys.argv) < 4:
        print("Usage: log_vector_win.py <query> <hit_path> <score> [source_tier]")
        return 1
    query = sys.argv[1]
    hit_path = sys.argv[2]
    score = float(sys.argv[3])
    source_tier = sys.argv[4] if len(sys.argv) > 4 else "eric"

    record = {
        "ts": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "query": query,
        "hit_path": hit_path,
        "score": score,
        "loaded_by_user": True,
        "source_tier": source_tier,
    }
    append_signal(SIGNAL_PATH, record)
    print(f"vector-win logged: {Path(hit_path).name} @ {score:.3f}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
