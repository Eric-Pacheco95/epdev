"""
local_model_router.py -- Jarvis Local Model Router

Stateless routing logic: given a task_type and list of tags, returns the
target inference tier: "local", "haiku", "sonnet", or "opus".

Zero side effects on import -- all logic is inside functions.
No module-level state or caching.
"""

import json
from datetime import datetime, timezone
from pathlib import Path


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _find_repo_root() -> Path:
    """Walk up from this file's location until local_model_config.json is found."""
    current = Path(__file__).resolve().parent
    while True:
        candidate = current / "local_model_config.json"
        if candidate.exists():
            return current
        parent = current.parent
        if parent == current:
            raise FileNotFoundError(
                "local_model_config.json not found in any parent directory of "
                + str(Path(__file__))
            )
        current = parent


def _load_config() -> dict:
    """Read local_model_config.json fresh on every call -- no module-level caching."""
    repo_root = _find_repo_root()
    config_path = repo_root / "local_model_config.json"
    with open(config_path, "r", encoding="utf-8") as f:
        return json.load(f)


def _record_first_time_review(task_type: str, repo_root: Path) -> None:
    """
    Append a review entry to data/local_routing_review.jsonl if this task_type
    has not previously been successfully reviewed (local_reviewed: true).

    The append is atomic: open 'a', write one JSON line + newline, close.
    """
    review_path = repo_root / "data" / "local_routing_review.jsonl"
    # Ensure data/ directory exists
    review_path.parent.mkdir(parents=True, exist_ok=True)

    # Check for prior successful review
    already_reviewed = False
    if review_path.exists():
        with open(review_path, "r", encoding="utf-8") as f:
            for raw_line in f:
                raw_line = raw_line.strip()
                if not raw_line:
                    continue
                try:
                    entry = json.loads(raw_line)
                    if entry.get("task_type") == task_type and entry.get("local_reviewed") is True:
                        already_reviewed = True
                        break
                except json.JSONDecodeError:
                    continue

    if already_reviewed:
        return

    iso_ts = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    record = json.dumps({
        "task_type": task_type,
        "routed_at": iso_ts,
        "local_reviewed": False,
    })
    # ASCII-only output
    record_ascii = record.encode("ascii", errors="replace").decode("ascii")
    with open(review_path, "a", encoding="ascii") as fh:
        fh.write(record_ascii + "\n")


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def route(task_type: str, tags: list) -> str:
    """
    Determine the inference target for a given task.

    Parameters
    ----------
    task_type : Identifier for the task (e.g. 'isc_format_validation').
    tags      : List of string tags associated with the task.

    Returns
    -------
    One of: "local", "sonnet" (PRD-A scope; haiku/opus added in PRD-B)

    Rules (in priority order):
    1. If ANY tag is in never_local_tags -> return "sonnet" (safe fallback, never local)
    2. If task_type is in auto_local_tasks -> write first-time review entry, return "local"
    3. Otherwise -> return "sonnet"
    """
    tags = [str(t) for t in tags]
    cfg = _load_config()
    repo_root = _find_repo_root()

    never_local = set(cfg.get("never_local_tags", []))
    auto_local = set(cfg.get("auto_local_tasks", []))

    # Rule 1: blocked tags take priority over everything
    for tag in tags:
        if tag in never_local:
            return "sonnet"

    # Rule 2: routable to local model
    if task_type in auto_local:
        _record_first_time_review(task_type, repo_root)
        return "local"

    # Rule 3: default cloud tier
    return "sonnet"
