"""Tests for tasklist_parser.py -- parse_tasklist and format_completion_only."""
from __future__ import annotations

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from tools.scripts.tasklist_parser import parse_tasklist, format_completion_only


def _write_tasklist(tmp_path: Path, content: str) -> Path:
    f = tmp_path / "tasklist.md"
    f.write_text(content, encoding="utf-8")
    return f


class TestParseTasklist:
    def test_empty_file_returns_structure(self, tmp_path):
        f = _write_tasklist(tmp_path, "")
        result = parse_tasklist(f)
        assert "tiers" in result
        assert "stats" in result
        assert result["stats"]["total_tasks"] == 0

    def test_parses_tier_header(self, tmp_path):
        content = "### Tier 1: Active Work\n- [ ] Do something\n"
        f = _write_tasklist(tmp_path, content)
        result = parse_tasklist(f)
        assert 1 in result["tiers"]
        assert result["tiers"][1]["name"] == "Active Work"

    def test_counts_checked_tasks(self, tmp_path):
        content = "### Tier 1: Active\n- [x] Done\n- [ ] Not done\n"
        f = _write_tasklist(tmp_path, content)
        result = parse_tasklist(f)
        assert result["stats"]["checked"] == 1
        assert result["stats"]["unchecked"] == 1
        assert result["stats"]["total_tasks"] == 2

    def test_tasks_in_tier(self, tmp_path):
        content = "### Tier 1: Active\n- [x] Task A\n- [ ] Task B\n"
        f = _write_tasklist(tmp_path, content)
        result = parse_tasklist(f)
        tasks = result["tiers"][1]["tasks"]
        assert len(tasks) == 2

    def test_multiple_tiers(self, tmp_path):
        content = (
            "### Tier 1: Active\n- [ ] Task A\n"
            "### Tier 2: Backlog\n- [ ] Task B\n"
        )
        f = _write_tasklist(tmp_path, content)
        result = parse_tasklist(f)
        assert 1 in result["tiers"]
        assert 2 in result["tiers"]

    def test_phase_header_parsed(self, tmp_path):
        content = "## Phase 5A: Autonomous\n- [ ] Task A\n"
        f = _write_tasklist(tmp_path, content)
        result = parse_tasklist(f)
        assert "5A" in result["phases"]

    def test_completion_pct_zero_when_none_done(self, tmp_path):
        content = "### Tier 1: Active\n- [ ] Task A\n- [ ] Task B\n"
        f = _write_tasklist(tmp_path, content)
        result = parse_tasklist(f)
        assert result["stats"]["completion_pct"] == 0

    def test_completion_pct_100_when_all_done(self, tmp_path):
        content = "### Tier 1: Active\n- [x] Task A\n- [x] Task B\n"
        f = _write_tasklist(tmp_path, content)
        result = parse_tasklist(f)
        assert result["stats"]["completion_pct"] == 100

    def test_source_field_is_filepath(self, tmp_path):
        f = _write_tasklist(tmp_path, "")
        result = parse_tasklist(f)
        assert str(f) in result["source"]


class TestFormatCompletionOnly:
    def _make_data(self, total=4, checked=2, unchecked=2, tiers=None):
        if tiers is None:
            tiers = {
                1: {"name": "Active", "tasks": [
                    {"checked": True}, {"checked": False}
                ]},
            }
        return {
            "stats": {
                "total_tasks": total,
                "checked": checked,
                "unchecked": unchecked,
                "completion_pct": int(100 * checked / total) if total else 0,
            },
            "tiers": tiers,
            "completion_summary": [],
        }

    def test_returns_string(self):
        data = self._make_data()
        result = format_completion_only(data)
        assert isinstance(result, str)

    def test_contains_total_count(self):
        data = self._make_data(total=10, checked=5, unchecked=5)
        result = format_completion_only(data)
        assert "10" in result

    def test_contains_checked_count(self):
        data = self._make_data(total=4, checked=3, unchecked=1)
        result = format_completion_only(data)
        assert "3 done" in result

    def test_contains_tier_line(self):
        data = self._make_data()
        result = format_completion_only(data)
        assert "Tier 1" in result

    def test_tier_ratio_in_output(self):
        data = self._make_data()
        result = format_completion_only(data)
        assert "1/2" in result

    def test_completion_summary_items(self):
        data = self._make_data()
        data["completion_summary"] = [{"phase": "5A", "status": "DONE"}]
        result = format_completion_only(data)
        assert "5A" in result
        assert "DONE" in result
