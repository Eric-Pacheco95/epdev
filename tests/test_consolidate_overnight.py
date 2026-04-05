"""Tests for consolidate_overnight.py -- generate_summary_md pure function."""

from tools.scripts.consolidate_overnight import generate_summary_md


def _empty_merge_result():
    return {"review_branch": "jarvis/review-2026-01-01", "merged": [], "conflicts": []}


def test_idle_is_success_when_no_branches():
    result = generate_summary_md([], _empty_merge_result(), [], "2026-01-01")
    assert "Idle Is Success" in result
    assert "Nothing to review" in result


def test_header_contains_date():
    result = generate_summary_md([], _empty_merge_result(), [], "2026-04-05")
    assert "# Overnight Summary -- 2026-04-05" in result


def test_all_merged_cleanly():
    branches = [{"branch": "jarvis/overnight-2026-01-01"}]
    merge_result = {
        "review_branch": "jarvis/review",
        "merged": [{"branch": "jarvis/overnight-2026-01-01", "commits": 3, "files": ["a.py"]}],
        "conflicts": [],
    }
    result = generate_summary_md(branches, merge_result, [], "2026-01-01")
    assert "1 branches merged cleanly" in result


def test_partial_merge_shows_counts():
    branches = [
        {"branch": "b1"},
        {"branch": "b2"},
    ]
    merge_result = {
        "review_branch": "jarvis/review",
        "merged": [{"branch": "b1", "commits": 1, "files": []}],
        "conflicts": [{"branch": "b2", "reason": "CONFLICT", "files": []}],
    }
    result = generate_summary_md(branches, merge_result, [], "2026-01-01")
    assert "1/2 merged" in result
    assert "1 conflicts" in result


def test_dispatcher_done_task():
    report = {
        "task_id": "TASK-001",
        "status": "done",
        "model": "claude-sonnet-4-6",
        "isc_passed": 3,
        "isc_total": 3,
        "diff_stat": "3 files changed",
    }
    result = generate_summary_md([], _empty_merge_result(), [report], "2026-01-01")
    assert "[DONE]" in result
    assert "TASK-001" in result
    assert "3 files changed" in result


def test_dispatcher_failed_task_shows_reason():
    report = {
        "task_id": "TASK-002",
        "status": "failed",
        "model": "claude-sonnet-4-6",
        "isc_passed": 1,
        "isc_total": 3,
        "failure_reason": "test suite red",
    }
    result = generate_summary_md([], _empty_merge_result(), [report], "2026-01-01")
    assert "[FAIL]" in result
    assert "test suite red" in result


def test_merged_branches_section_truncates_files():
    files = [f"file_{i}.py" for i in range(10)]
    merge_result = {
        "review_branch": "jarvis/review",
        "merged": [{"branch": "b1", "commits": 5, "files": files}],
        "conflicts": [],
    }
    result = generate_summary_md([{"branch": "b1"}], merge_result, [], "2026-01-01")
    assert "and 5 more" in result


def test_conflicts_section_present():
    merge_result = {
        "review_branch": "jarvis/review",
        "merged": [],
        "conflicts": [{"branch": "b1", "reason": "merge conflict", "files": ["x.py"]}],
    }
    result = generate_summary_md([{"branch": "b1"}], merge_result, [], "2026-01-01")
    assert "## Conflicts" in result
    assert "merge conflict" in result


def test_next_steps_merge_commands_present():
    merge_result = {
        "review_branch": "jarvis/review",
        "merged": [{"branch": "b1", "commits": 1, "files": []}],
        "conflicts": [],
    }
    result = generate_summary_md([{"branch": "b1"}], merge_result, [], "2026-01-01")
    assert "git log --oneline" in result
    assert "git diff" in result
