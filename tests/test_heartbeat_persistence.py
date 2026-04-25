"""Tests for jarvis_heartbeat.py -- persistence and config helpers."""
from __future__ import annotations

import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from tools.scripts.jarvis_heartbeat import (
    resolve_root,
    load_previous,
    save_snapshot,
    get_snapshot_paths,
    _load_cooldown_state,
    _save_cooldown_state,
)
import tools.scripts.jarvis_heartbeat as hb


class TestResolveRoot:
    def test_absolute_path_returned_as_is(self, tmp_path):
        cfg = {"root_dir": str(tmp_path)}
        result = resolve_root(cfg)
        assert result == tmp_path

    def test_relative_path_resolved_to_repo(self):
        cfg = {"root_dir": "."}
        result = resolve_root(cfg)
        assert result.is_absolute()

    def test_missing_key_defaults_to_dot(self):
        result = resolve_root({})
        assert result.is_absolute()


class TestLoadPrevious:
    def test_missing_file_returns_none(self, tmp_path):
        assert load_previous(tmp_path / "missing.json") is None

    def test_loads_valid_json(self, tmp_path):
        f = tmp_path / "latest.json"
        f.write_text(json.dumps({"ts": "2026-01-01T00:00:00Z"}), encoding="utf-8")
        result = load_previous(f)
        assert result["ts"] == "2026-01-01T00:00:00Z"

    def test_invalid_json_returns_none(self, tmp_path):
        f = tmp_path / "bad.json"
        f.write_text("not json", encoding="utf-8")
        assert load_previous(f) is None


class TestSaveSnapshot:
    def test_writes_latest_file(self, tmp_path):
        latest = tmp_path / "latest.json"
        history = tmp_path / "history.jsonl"
        snap = {"ts": "2026-01-01T00:00:00Z", "signals": 5}
        save_snapshot(snap, latest, history)
        assert latest.exists()
        assert json.loads(latest.read_text(encoding="utf-8"))["signals"] == 5

    def test_appends_to_history(self, tmp_path):
        latest = tmp_path / "latest.json"
        history = tmp_path / "history.jsonl"
        snap1 = {"ts": "2026-01-01T00:00:00Z"}
        snap2 = {"ts": "2026-01-02T00:00:00Z"}
        save_snapshot(snap1, latest, history)
        save_snapshot(snap2, latest, history)
        lines = history.read_text(encoding="utf-8").strip().splitlines()
        assert len(lines) == 2

    def test_latest_overwritten_each_time(self, tmp_path):
        latest = tmp_path / "latest.json"
        history = tmp_path / "history.jsonl"
        save_snapshot({"ts": "2026-01-01T00:00:00Z"}, latest, history)
        save_snapshot({"ts": "2026-01-02T00:00:00Z"}, latest, history)
        data = json.loads(latest.read_text(encoding="utf-8"))
        assert data["ts"] == "2026-01-02T00:00:00Z"


class TestGetSnapshotPaths:
    def test_returns_tuple_of_paths(self, tmp_path, monkeypatch):
        cfg = {"snapshot_dir": "snaps"}
        latest, history = get_snapshot_paths(cfg, tmp_path)
        assert latest.name == "heartbeat_latest.json"
        assert history.name == "heartbeat_history.jsonl"

    def test_creates_snapshot_dir(self, tmp_path):
        cfg = {"snapshot_dir": "new_snaps"}
        get_snapshot_paths(cfg, tmp_path)
        assert (tmp_path / "new_snaps").is_dir()


class TestCooldownState:
    def test_missing_file_returns_empty(self, tmp_path):
        assert _load_cooldown_state(tmp_path) == {}

    def test_save_and_load_roundtrip(self, tmp_path):
        state = {"isc_ratio": "2026-01-01T00:00:00Z"}
        _save_cooldown_state(tmp_path, state)
        loaded = _load_cooldown_state(tmp_path)
        assert loaded == state

    def test_invalid_json_returns_empty(self, tmp_path):
        f = tmp_path / "cooldown_state.json"
        f.write_text("bad json", encoding="utf-8")
        assert _load_cooldown_state(tmp_path) == {}
