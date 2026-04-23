"""Tests for tools/scripts/verify_costs_rollup.py."""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from tools.scripts.verify_costs_rollup import check, verify


def _make_window(spend=1.0, per_model=None, per_skill=None, daily=None, session=None):
    if per_model is None:
        per_model = [{"model": "sonnet", "share_pct": 100.0, "cost_usd": 1.0}]
    if per_skill is None:
        per_skill = [{"skill": "/research", "cost_usd": 1.0}]
    if daily is None:
        daily = {}
    if session is None:
        session = {
            "avg_usd": 0.5, "session_count": 2,
            "most_expensive": None, "cost_per_1k_tokens_usd": 0.01,
        }
    return {
        "spend_usd": spend,
        "spend_prev_window_usd": 0.0,
        "input_tokens_total": 100,
        "output_tokens_total": 50,
        "cache_read_tokens_total": 0,
        "cache_creation_tokens_total": 0,
        "per_day_avg_usd": 0.1,
        "daily_spend_usd": daily,
        "budget": {"monthly_usd": 20.0, "mtd_usd": 1.0, "pct": 5.0},
        "per_model": per_model,
        "per_skill": per_skill,
        "session_rollups": session,
    }


def _make_rollup(windows=None, event_count=100, transcript_count=5):
    if windows is None:
        windows = {k: _make_window() for k in ("7d", "30d", "90d", "ytd")}
    return {
        "windows": windows,
        "source_event_count": event_count,
        "source_transcript_count": transcript_count,
        "status": "ok",
    }


# --- check() unit tests ---

def test_check_passes_on_true():
    failures = []
    result = check(True, "msg", failures)
    assert result is True
    assert failures == []


def test_check_fails_on_false():
    failures = []
    result = check(False, "bad thing", failures)
    assert result is False
    assert failures == ["bad thing"]


def test_check_accumulates_failures():
    failures = []
    check(False, "err1", failures)
    check(False, "err2", failures)
    assert len(failures) == 2


# --- verify() integration tests ---

def test_verify_valid_rollup(tmp_path):
    rollup = _make_rollup()
    f = tmp_path / "costs_rollup.json"
    f.write_text(json.dumps(rollup), encoding="utf-8")
    assert verify(f) is True


def test_verify_missing_file(tmp_path):
    assert verify(tmp_path / "nonexistent.json") is False


def test_verify_invalid_json(tmp_path):
    f = tmp_path / "costs_rollup.json"
    f.write_text("not json", encoding="utf-8")
    assert verify(f) is False


def test_verify_missing_windows_key(tmp_path):
    rollup = {"source_event_count": 1}
    f = tmp_path / "costs_rollup.json"
    f.write_text(json.dumps(rollup), encoding="utf-8")
    assert verify(f) is False


def test_verify_missing_window(tmp_path):
    windows = {k: _make_window() for k in ("7d", "30d", "90d")}  # missing ytd
    rollup = _make_rollup(windows=windows)
    f = tmp_path / "costs_rollup.json"
    f.write_text(json.dumps(rollup), encoding="utf-8")
    assert verify(f) is False


def test_verify_share_pct_not_100(tmp_path):
    per_model = [
        {"model": "sonnet", "share_pct": 60.0, "cost_usd": 0.6},
        {"model": "opus", "share_pct": 20.0, "cost_usd": 0.4},
    ]
    windows = {k: _make_window(per_model=per_model) for k in ("7d", "30d", "90d", "ytd")}
    rollup = _make_rollup(windows=windows)
    f = tmp_path / "costs_rollup.json"
    f.write_text(json.dumps(rollup), encoding="utf-8")
    assert verify(f) is False


def test_verify_per_skill_not_sorted(tmp_path):
    per_skill = [
        {"skill": "/cheap", "cost_usd": 0.1},
        {"skill": "/expensive", "cost_usd": 1.0},
    ]
    windows = {k: _make_window(per_skill=per_skill) for k in ("7d", "30d", "90d", "ytd")}
    rollup = _make_rollup(windows=windows)
    f = tmp_path / "costs_rollup.json"
    f.write_text(json.dumps(rollup), encoding="utf-8")
    assert verify(f) is False


def test_verify_zero_event_count(tmp_path):
    rollup = _make_rollup(event_count=0)
    f = tmp_path / "costs_rollup.json"
    f.write_text(json.dumps(rollup), encoding="utf-8")
    assert verify(f) is False
