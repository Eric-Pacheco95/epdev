"""Tests for tasklist_parser pure functions."""

from tools.scripts.tasklist_parser import (
    parse_task_line,
    parse_project_line,
    parse_completion_table,
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
