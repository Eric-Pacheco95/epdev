"""Tests for tools/scripts/update_status.py pure helper functions."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import tools.scripts.update_status as us


# ---------------------------------------------------------------------------
# _parse_section
# ---------------------------------------------------------------------------

SAMPLE_DOC = """\
## Done This Session
- **Phase 5E** — shipped

## Pending Efforts

### Effort A — refactor
**State:** in progress

## Hard Constraints
- nothing

## Some Other Section
content
"""


def test_parse_section_found():
    result = us._parse_section(SAMPLE_DOC, "Done This Session")
    assert "Phase 5E" in result


def test_parse_section_stops_at_next_h2():
    result = us._parse_section(SAMPLE_DOC, "Done This Session")
    assert "Pending Efforts" not in result


def test_parse_section_missing_returns_empty():
    assert us._parse_section(SAMPLE_DOC, "Nonexistent Section") == ""


def test_parse_section_last_in_doc():
    result = us._parse_section(SAMPLE_DOC, "Some Other Section")
    assert "content" in result


# ---------------------------------------------------------------------------
# _extract_bullet_items
# ---------------------------------------------------------------------------

def test_extract_bullet_items_basic():
    text = "- **item one**\n- item two\nignored line\n"
    items = us._extract_bullet_items(text)
    assert len(items) == 2
    assert items[0] == "- **item one**"


def test_extract_bullet_items_empty():
    assert us._extract_bullet_items("") == []


def test_extract_bullet_items_no_bullets():
    assert us._extract_bullet_items("just a line\nanother line") == []


def test_extract_bullet_items_indented_bullets():
    text = "  - item one\n  - item two\n"
    items = us._extract_bullet_items(text)
    assert len(items) == 2


# ---------------------------------------------------------------------------
# _pending_efforts_to_bullets
# ---------------------------------------------------------------------------

EFFORTS_BLOCK = """\
### Effort A — deploy the new router
**State:** ready to ship
**Blocked on:** nothing

### Session B — run falsification
**State:** waiting for CI
**Blocked on:** CI queue
"""


def test_pending_efforts_to_bullets_count():
    result = us._pending_efforts_to_bullets(EFFORTS_BLOCK)
    lines = [l for l in result.splitlines() if l.startswith("- ")]
    assert len(lines) == 2


def test_pending_efforts_to_bullets_strips_effort_prefix():
    result = us._pending_efforts_to_bullets(EFFORTS_BLOCK)
    assert "deploy the new router" in result
    assert "Effort A" not in result


def test_pending_efforts_to_bullets_includes_state():
    result = us._pending_efforts_to_bullets(EFFORTS_BLOCK)
    assert "ready to ship" in result


def test_pending_efforts_to_bullets_suppresses_unblocked():
    result = us._pending_efforts_to_bullets(EFFORTS_BLOCK)
    # "nothing" is in _unblocked — should not appear
    assert "[blocked: nothing]" not in result


def test_pending_efforts_to_bullets_shows_real_blocker():
    result = us._pending_efforts_to_bullets(EFFORTS_BLOCK)
    assert "CI queue" in result


def test_pending_efforts_to_bullets_empty():
    assert us._pending_efforts_to_bullets("") == ""


# ---------------------------------------------------------------------------
# _first_done_label
# ---------------------------------------------------------------------------

def test_first_done_label_with_bold():
    text = "- **Phase 5E COMPLETE** — shipped all the things\n- **item two**"
    label = us._first_done_label(text)
    assert label == "Phase 5E COMPLETE"


def test_first_done_label_no_bold():
    text = "- plain text item"
    label = us._first_done_label(text)
    assert label == "plain text item"


def test_first_done_label_no_bullets():
    label = us._first_done_label("nothing here")
    assert label == "session complete"


# ---------------------------------------------------------------------------
# _update_last_updated_line
# ---------------------------------------------------------------------------

STATUS_TEMPLATE = """\
## Last Updated: 2026-01-01 — something old

## Recent Wins
- old win

## Queued Next Session
- old task
"""


def test_update_last_updated_line_replaces():
    result = us._update_last_updated_line(STATUS_TEMPLATE, "2026-04-28 — new thing")
    assert "## Last Updated: 2026-04-28 — new thing" in result


def test_update_last_updated_line_leaves_other_sections():
    result = us._update_last_updated_line(STATUS_TEMPLATE, "2026-04-28 — new thing")
    assert "## Recent Wins" in result
    assert "old win" in result


# ---------------------------------------------------------------------------
# _replace_section_body
# ---------------------------------------------------------------------------

def test_replace_section_body_basic():
    result = us._replace_section_body(STATUS_TEMPLATE, "Queued Next Session", "- new task")
    assert "- new task" in result
    assert "- old task" not in result


def test_replace_section_body_keeps_header():
    result = us._replace_section_body(STATUS_TEMPLATE, "Queued Next Session", "- new task")
    assert "## Queued Next Session" in result


def test_replace_section_body_preserves_other_sections():
    result = us._replace_section_body(STATUS_TEMPLATE, "Queued Next Session", "- new task")
    assert "## Recent Wins" in result


# ---------------------------------------------------------------------------
# _prepend_to_section
# ---------------------------------------------------------------------------

def test_prepend_to_section_adds_entry():
    result = us._prepend_to_section(STATUS_TEMPLATE, "Recent Wins", "- brand new win")
    assert "- brand new win" in result


def test_prepend_to_section_keeps_existing():
    result = us._prepend_to_section(STATUS_TEMPLATE, "Recent Wins", "- brand new win")
    assert "- old win" in result


def test_prepend_to_section_new_entry_before_old():
    result = us._prepend_to_section(STATUS_TEMPLATE, "Recent Wins", "- brand new win")
    new_idx = result.index("brand new win")
    old_idx = result.index("old win")
    assert new_idx < old_idx


# ---------------------------------------------------------------------------
# _build_updated_status integration
# ---------------------------------------------------------------------------

HANDOFF_DOC = """\
## Done This Session
- **Router refactor** — fully shipped
- **Second item** — done too

## Pending Efforts

### Effort A — next thing to do
**State:** waiting on CI
**Blocked on:** CI queue

## Hard Constraints
- Memory cap not yet increased
"""

STATUS_DOC = """\
## Last Updated: 2026-01-01 — old

## Recent Wins
- old win

## Queued Next Session
- old task

## Current Blockers
- old blocker

## Current Focus
manually maintained
"""


def test_build_updated_status_updates_last_updated():
    result = us._build_updated_status(HANDOFF_DOC, STATUS_DOC)
    assert "Router refactor" in result
    assert "2026-01-01" not in result


def test_build_updated_status_prepends_win():
    result = us._build_updated_status(HANDOFF_DOC, STATUS_DOC)
    assert "Router refactor" in result
    assert "old win" in result


def test_build_updated_status_updates_queued():
    result = us._build_updated_status(HANDOFF_DOC, STATUS_DOC)
    assert "next thing to do" in result
    assert "old task" not in result


def test_build_updated_status_updates_blockers():
    result = us._build_updated_status(HANDOFF_DOC, STATUS_DOC)
    assert "Memory cap" in result
    assert "old blocker" not in result


def test_build_updated_status_preserves_manual_section():
    result = us._build_updated_status(HANDOFF_DOC, STATUS_DOC)
    assert "Current Focus" in result
    assert "manually maintained" in result
