"""Tests for tasklist_parser pure functions."""

from tools.scripts.tasklist_parser import (
    parse_task_line,
    parse_project_line,
    parse_completion_table,
    filter_tasks,
    _sanitize_ascii,
)


def test_parse_task_line_checked():
    line = "- [x] **4E-S1: Deploy dispatcher** -- Shipped autonomous dispatcher (2026-03-28)"
    result = parse_task_line(line)
    assert result is not None
    assert result["checked"] is True
    assert result["phase_tag"] == "4E-S1"
    assert "Deploy dispatcher" in result["title"]
    assert result["completed_date"] == "2026-03-28"


def test_parse_task_line_unchecked():
    line = "- [ ] **Slack Bot Socket Mode setup** -- slash commands"
    result = parse_task_line(line)
    assert result is not None
    assert result["checked"] is False
    assert result["title"] == "Slack Bot Socket Mode setup"
    assert result["phase_tag"] is None


def test_parse_task_line_no_description():
    line = "- [x] **5A: Design review** (2026-03-30)"
    result = parse_task_line(line)
    assert result is not None
    assert result["checked"] is True
    assert result["completed_date"] == "2026-03-30"


def test_parse_task_line_not_a_task():
    assert parse_task_line("## Section header") is None
    assert parse_task_line("plain text") is None
    assert parse_task_line("") is None


def test_parse_project_line_valid():
    line = "| crypto-bot | active | P1, G1 | epdev | Fix scope |"
    result = parse_project_line(line)
    assert result is not None
    assert result["name"] == "crypto-bot"
    assert result["status"] == "active"


def test_parse_project_line_header():
    assert parse_project_line("| Project | Status | Health | Owner | Next |") is None


def test_parse_project_line_separator():
    assert parse_project_line("| --- | --- | --- | --- | --- |") is None


def test_parse_completion_table_valid():
    line = "| Phase 4 | COMPLETE | 0 |"
    result = parse_completion_table(line)
    assert result is not None
    assert result["phase"] == "Phase 4"
    assert result["status"] == "COMPLETE"
    assert result["remaining"] == "0"


def test_parse_completion_table_header():
    assert parse_completion_table("| Phase | Status | Remaining |") is None


def _make_data(tier_tasks=None, phase_tasks=None):
    """Build minimal data dict for filter_tasks."""
    return {
        "tiers": {1: {"tasks": tier_tasks or []}},
        "phases": {"5A": {"tasks": phase_tasks or []}},
    }


def test_filter_tasks_no_filter_returns_all():
    tasks = [{"checked": True, "title": "a"}, {"checked": False, "title": "b"}]
    data = _make_data(tier_tasks=tasks)
    result = filter_tasks(data, tier=None, status=None, phase=None)
    assert len(result) == 2


def test_filter_tasks_by_status_checked():
    tasks = [{"checked": True, "title": "done"}, {"checked": False, "title": "open"}]
    data = _make_data(tier_tasks=tasks)
    result = filter_tasks(data, tier=None, status="checked", phase=None)
    assert all(t["checked"] for t in result)
    assert len(result) == 1


def test_filter_tasks_by_status_unchecked():
    tasks = [{"checked": True}, {"checked": False}, {"checked": False}]
    data = _make_data(tier_tasks=tasks)
    result = filter_tasks(data, tier=None, status="unchecked", phase=None)
    assert len(result) == 2
    assert all(not t["checked"] for t in result)


def test_filter_tasks_by_tier():
    tier1 = [{"checked": False, "title": "t1"}]
    data = {
        "tiers": {1: {"tasks": tier1}, 2: {"tasks": [{"checked": False}]}},
        "phases": {},
    }
    result = filter_tasks(data, tier=1, status=None, phase=None)
    assert all(t.get("_tier") == 1 for t in result)


def test_filter_tasks_by_phase():
    phase_tasks = [{"checked": False, "title": "p", "phase_tag": None}]
    data = _make_data(phase_tasks=phase_tasks)
    result = filter_tasks(data, tier=None, status=None, phase="5A")
    assert len(result) == 1


def test_sanitize_ascii_arrows():
    assert _sanitize_ascii("a \u2192 b") == "a -> b"


def test_sanitize_ascii_em_dash():
    assert _sanitize_ascii("foo\u2014bar") == "foo--bar"


def test_sanitize_ascii_smart_quotes():
    assert _sanitize_ascii("\u201chello\u201d") == '"hello"'


def test_sanitize_ascii_no_change():
    assert _sanitize_ascii("plain text 123") == "plain text 123"


def test_sanitize_ascii_ellipsis():
    assert _sanitize_ascii("wait\u2026") == "wait..."
