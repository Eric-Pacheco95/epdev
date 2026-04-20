"""Pytest tests for tools/scripts/rotate_events.py — config loading, file discovery, rollup."""

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from tools.scripts.rotate_events import load_config, get_event_files, rollup_month, resolve_root, REPO_ROOT


class TestLoadConfig:
    def test_missing_file_returns_defaults(self, tmp_path):
        cfg = load_config(tmp_path / "nonexistent.json")
        assert "retention" in cfg
        assert cfg["retention"]["raw_days"] == 90

    def test_valid_config(self, tmp_path):
        config_file = tmp_path / "config.json"
        config_file.write_text(json.dumps({"retention": {"raw_days": 30}}))
        cfg = load_config(config_file)
        assert cfg["retention"]["raw_days"] == 30

    def test_invalid_json_returns_defaults(self, tmp_path):
        config_file = tmp_path / "config.json"
        config_file.write_text("not json{{{")
        cfg = load_config(config_file)
        assert cfg["retention"]["raw_days"] == 90


class TestGetEventFiles:
    def test_empty_dir(self, tmp_path):
        assert get_event_files(tmp_path) == []

    def test_nonexistent_dir(self, tmp_path):
        assert get_event_files(tmp_path / "nope") == []

    def test_finds_dated_jsonl(self, tmp_path):
        (tmp_path / "2026-03-01.jsonl").write_text("")
        (tmp_path / "2026-03-02.jsonl").write_text("")
        (tmp_path / "not-a-date.jsonl").write_text("")  # should be skipped
        result = get_event_files(tmp_path)
        assert len(result) == 2

    def test_sorted_by_date(self, tmp_path):
        (tmp_path / "2026-03-15.jsonl").write_text("")
        (tmp_path / "2026-03-01.jsonl").write_text("")
        result = get_event_files(tmp_path)
        assert result[0][1] < result[1][1]

    def test_returns_datetime_with_tz(self, tmp_path):
        (tmp_path / "2026-01-15.jsonl").write_text("")
        result = get_event_files(tmp_path)
        assert result[0][1].tzinfo == timezone.utc


class TestRollupMonth:
    def test_dry_run_does_not_create_file(self, tmp_path):
        events_dir = tmp_path / "events"
        events_dir.mkdir()
        f = events_dir / "2026-01-01.jsonl"
        f.write_text('{"tool":"Read","session_id":"s1","success":true}\n')
        rollup_month(events_dir, 2026, 1, [f], execute=False)
        assert not (events_dir / "rollups" / "2026-01_summary.json").exists()

    def test_execute_creates_rollup(self, tmp_path):
        events_dir = tmp_path / "events"
        events_dir.mkdir()
        f = events_dir / "2026-01-01.jsonl"
        f.write_text('{"tool":"Read","session_id":"s1","success":true}\n'
                      '{"tool":"Edit","session_id":"s1","success":false}\n')
        rollup_month(events_dir, 2026, 1, [f], execute=True)
        rollup = events_dir / "rollups" / "2026-01_summary.json"
        assert rollup.exists()
        data = json.loads(rollup.read_text())
        assert data["total_records"] == 2
        assert data["total_failures"] == 1
        assert data["unique_sessions"] == 1

    def test_skips_existing_rollup(self, tmp_path):
        events_dir = tmp_path / "events"
        rollup_dir = events_dir / "rollups"
        rollup_dir.mkdir(parents=True)
        rollup_path = rollup_dir / "2026-01_summary.json"
        rollup_path.write_text('{"existing": true}')
        result = rollup_month(events_dir, 2026, 1, [], execute=True)
        assert result == rollup_path
        # Original content unchanged
        assert json.loads(rollup_path.read_text())["existing"] is True


class TestResolveRoot:
    def test_absolute_path_returned_as_is(self, tmp_path):
        cfg = {"root_dir": str(tmp_path)}
        result = resolve_root(cfg)
        assert result == tmp_path

    def test_relative_path_resolved_under_repo_root(self):
        cfg = {"root_dir": "data/events"}
        result = resolve_root(cfg)
        assert result == REPO_ROOT / "data" / "events"

    def test_default_dot_resolves_to_repo_root(self):
        cfg = {}
        result = resolve_root(cfg)
        assert result == REPO_ROOT
