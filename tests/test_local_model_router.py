"""Tests for tools/scripts/local_model_router.py."""
import json
import sys
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import tools.scripts.local_model_router as lmr

_BASE_CONFIG = {
    "provider": "ollama",
    "model": "test-model",
    "base_url": "http://127.0.0.1:11434",
    "auto_local_tasks": ["isc_format_validation", "signal_extraction"],
    "never_local_tags": ["security", "tier_0"],
}


def _route(task_type, tags, config=None, tmp_path=None):
    cfg = config or _BASE_CONFIG
    fake_root = tmp_path or Path("/tmp/fake_root")
    with patch.object(lmr, "_load_config", return_value=cfg), \
         patch.object(lmr, "_find_repo_root", return_value=fake_root), \
         patch.object(lmr, "_record_first_time_review"):
        return lmr.route(task_type, tags)


# --- route() ---

def test_route_auto_local_task_no_blocked_tags():
    result = _route("isc_format_validation", [])
    assert result == "local"


def test_route_blocked_tag_overrides_auto_local():
    result = _route("isc_format_validation", ["security"])
    assert result == "sonnet"


def test_route_tier0_tag_blocked():
    result = _route("signal_extraction", ["tier_0"])
    assert result == "sonnet"


def test_route_unknown_task_defaults_sonnet():
    result = _route("unknown_task", [])
    assert result == "sonnet"


def test_route_unknown_task_with_safe_tags_still_sonnet():
    result = _route("my_custom_task", ["debug", "low_stakes"])
    assert result == "sonnet"


def test_route_auto_local_with_safe_tags():
    result = _route("signal_extraction", ["low_stakes", "batch"])
    assert result == "local"


# --- _record_first_time_review ---

def test_record_first_time_creates_entry(tmp_path):
    lmr._record_first_time_review("new_task", tmp_path)
    review_path = tmp_path / "data" / "local_routing_review.jsonl"
    assert review_path.exists()
    lines = [ln for ln in review_path.read_text(encoding="utf-8").splitlines() if ln.strip()]
    assert len(lines) == 1
    entry = json.loads(lines[0])
    assert entry["task_type"] == "new_task"
    assert entry["local_reviewed"] is False


def test_record_first_time_idempotent_if_already_reviewed(tmp_path):
    review_path = tmp_path / "data" / "local_routing_review.jsonl"
    review_path.parent.mkdir(parents=True)
    existing = json.dumps({"task_type": "known_task", "local_reviewed": True})
    review_path.write_text(existing + "\n", encoding="ascii")

    lmr._record_first_time_review("known_task", tmp_path)

    lines = [ln for ln in review_path.read_text(encoding="utf-8").splitlines() if ln.strip()]
    assert len(lines) == 1  # no new entry appended


def test_record_appends_if_not_yet_reviewed(tmp_path):
    review_path = tmp_path / "data" / "local_routing_review.jsonl"
    review_path.parent.mkdir(parents=True)
    existing = json.dumps({"task_type": "known_task", "local_reviewed": False})
    review_path.write_text(existing + "\n", encoding="ascii")

    lmr._record_first_time_review("new_task", tmp_path)

    lines = [ln for ln in review_path.read_text(encoding="utf-8").splitlines() if ln.strip()]
    assert len(lines) == 2
