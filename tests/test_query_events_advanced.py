"""Advanced tests for query_events.compute_metrics() -- multi-session scenarios."""

from query_events import compute_metrics


def _rec(hook="PostToolUse", tool="Bash", sid="s1", ts="2026-03-28T10:00:00Z",
         success=True, **kw):
    r = {"hook": hook, "tool": tool, "session_id": sid, "ts": ts, "success": success}
    r.update(kw)
    return r


def test_multi_session_count():
    records = [
        _rec(hook="Stop", tool="_session", sid="s1", ts="2026-03-28T10:00:00Z"),
        _rec(hook="Stop", tool="_session", sid="s2", ts="2026-03-28T14:00:00Z"),
        _rec(hook="Stop", tool="_session", sid="s3", ts="2026-03-29T09:00:00Z"),
    ]
    m = compute_metrics(records)
    assert m["sessions_total"] == 3


def test_sessions_per_day():
    records = [
        _rec(hook="Stop", tool="_session", sid="s1", ts="2026-03-27T10:00:00Z"),
        _rec(hook="Stop", tool="_session", sid="s2", ts="2026-03-28T10:00:00Z"),
        _rec(hook="Stop", tool="_session", sid="s3", ts="2026-03-28T14:00:00Z"),
        _rec(hook="Stop", tool="_session", sid="s4", ts="2026-03-29T09:00:00Z"),
    ]
    m = compute_metrics(records)
    assert m["sessions_total"] == 4
    assert m["unique_days_with_data"] == 3
    # 4 sessions / 3 days
    assert m["sessions_per_day"] == round(4 / 3, 2)


def test_isc_gap_sessions():
    """Sessions with failures should be tracked."""
    records = [
        _rec(tool="Bash", sid="s1", success=False),
        _rec(tool="Read", sid="s1", success=True),
        _rec(tool="Write", sid="s2", success=False),
    ]
    m = compute_metrics(records)
    assert m["isc_gap_sessions"] == 2  # both s1 and s2 have failures


def test_intent_calls_counted():
    records = [
        _rec(hook="PreToolUse", tool="Bash"),
        _rec(hook="PreToolUse", tool="Read"),
        _rec(tool="Bash"),  # PostToolUse
    ]
    m = compute_metrics(records)
    assert m["intent_calls"] == 2
    assert m["total_tool_calls"] == 1


def test_session_tool_excluded():
    """_session tool records should not count as tool calls."""
    records = [
        _rec(tool="Bash"),
        _rec(tool="_session", hook="PostToolUse"),  # should be excluded
    ]
    m = compute_metrics(records)
    assert m["total_tool_calls"] == 1
