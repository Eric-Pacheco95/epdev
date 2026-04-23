"""Tests for tools/scripts/isc_template_monitor.py."""
import json
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import tools.scripts.isc_template_monitor as itm


def _write_log(tmp_path, rows):
    f = tmp_path / "isc_template_usage.jsonl"
    f.write_text(
        "\n".join(json.dumps(r) for r in rows) + "\n",
        encoding="utf-8",
    )
    return f


def test_missing_log_returns_0(tmp_path, monkeypatch):
    monkeypatch.setattr(sys, "argv", ["prog"])
    with patch.object(itm, "USAGE_LOG", tmp_path / "nonexistent.jsonl"):
        assert itm.main() == 0


def test_counts_presets(tmp_path, monkeypatch):
    rows = [
        {"ts": "2026-01-01T00:00:00Z", "preset": "fix_lint"},
        {"ts": "2026-01-02T00:00:00Z", "preset": "fix_lint"},
        {"ts": "2026-01-03T00:00:00Z", "preset": "remove_dead_code"},
    ]
    f = _write_log(tmp_path, rows)
    monkeypatch.setattr(sys, "argv", ["prog"])
    with patch.object(itm, "USAGE_LOG", f):
        assert itm.main() == 0


def test_since_days_filters_old_rows(tmp_path, monkeypatch):
    old_ts = (datetime.now(timezone.utc) - timedelta(days=30)).strftime("%Y-%m-%dT%H:%M:%SZ")
    new_ts = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    rows = [
        {"ts": old_ts, "preset": "old_preset"},
        {"ts": new_ts, "preset": "new_preset"},
    ]
    f = _write_log(tmp_path, rows)
    monkeypatch.setattr(sys, "argv", ["prog", "--since-days", "7"])
    with patch.object(itm, "USAGE_LOG", f):
        assert itm.main() == 0


def test_skips_invalid_json_lines(tmp_path, monkeypatch):
    f = tmp_path / "isc_template_usage.jsonl"
    f.write_text(
        "not json\n" + json.dumps({"ts": "2026-01-01T00:00:00Z", "preset": "foo"}) + "\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(sys, "argv", ["prog"])
    with patch.object(itm, "USAGE_LOG", f):
        assert itm.main() == 0


def test_empty_file_returns_0(tmp_path, monkeypatch):
    f = tmp_path / "isc_template_usage.jsonl"
    f.write_text("", encoding="utf-8")
    monkeypatch.setattr(sys, "argv", ["prog"])
    with patch.object(itm, "USAGE_LOG", f):
        assert itm.main() == 0
