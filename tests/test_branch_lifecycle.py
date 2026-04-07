"""Tests for branch_lifecycle.format_report."""

from tools.scripts.branch_lifecycle import format_report


def _make_branch(name, age_days, commit_count, diff_summary, is_stale=False, is_merged=False):
    return {
        "name": name,
        "age_days": age_days,
        "commit_count": commit_count,
        "diff_summary": diff_summary,
        "is_stale": is_stale,
        "is_merged": is_merged,
    }


def test_format_report_empty():
    result = format_report([])
    assert result == "No Jarvis autonomous branches found."


def test_format_report_active_branch():
    branch = _make_branch("jarvis/feature-x", 3, 2, "1 file changed")
    result = format_report([branch])
    assert "ACTIVE" in result
    assert "jarvis/feature-x" in result
    assert "3d old" in result


def test_format_report_stale_branch():
    branch = _make_branch("jarvis/old-feature", 10, 5, "3 files changed", is_stale=True)
    result = format_report([branch])
    assert "STALE" in result
    assert "jarvis/old-feature" in result
    assert "10d old" in result


def test_format_report_merged_branch():
    branch = _make_branch("jarvis/done", 15, 1, "2 files changed", is_merged=True)
    result = format_report([branch])
    assert "MERGED" in result
    assert "jarvis/done" in result


def test_format_report_totals_line():
    branches = [
        _make_branch("jarvis/active", 2, 1, "x"),
        _make_branch("jarvis/stale", 10, 3, "y", is_stale=True),
        _make_branch("jarvis/merged", 20, 1, "z", is_merged=True),
    ]
    result = format_report(branches)
    assert "Total: 3" in result
    assert "Stale: 1" in result
    assert "Merged: 1" in result
    assert "Active: 1" in result


def test_format_report_multiple_stale_sorted_by_age():
    branches = [
        _make_branch("jarvis/oldest", 30, 2, "x", is_stale=True),
        _make_branch("jarvis/newer", 8, 1, "y", is_stale=True),
    ]
    result = format_report(branches)
    idx_oldest = result.index("jarvis/oldest")
    idx_newer = result.index("jarvis/newer")
    assert idx_oldest < idx_newer  # oldest appears first (sorted descending by age)
