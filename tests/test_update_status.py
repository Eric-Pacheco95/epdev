"""Tests for tools/scripts/update_status.py."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from tools.scripts.update_status import (
    _parse_section,
    _extract_bullet_items,
    _pending_efforts_to_bullets,
    _first_done_label,
    _replace_section_body,
    _prepend_to_section,
    _update_last_updated_line,
    _build_updated_status,
)

SAMPLE_STATUS = """\
## Last Updated: 2026-01-01 — initial

## Current Focus
Shipping Phase 5.

## Queued Next Session

- old queue item

## Recent Wins

- **2026-01-01**: Old win

## Current Blockers

- old blocker

## Signal Pipeline Health
manual section
"""

SAMPLE_HANDOFF = """\
# Session Handoff

## Done This Session
- **Phase 5E Auth** — completed the auth module
- **Test coverage** — added 20 tests

## Hard Constraints
- Moralis cap resets 2026-05-03
- Redis not available locally

## Pending Efforts

### Effort A — Deploy to prod
**State:** ready to deploy
**Blocked on:** nothing — ready to build

### Effort B — Crypto bot restart
**State:** waiting for cap reset
**Blocked on:** Moralis cap resets 2026-05-03
"""


class TestParseSection:
    def test_extracts_section_body(self):
        text = "## Done This Session\n- item one\n- item two\n\n## Next Section\nstuff"
        body = _parse_section(text, "Done This Session")
        assert "item one" in body
        assert "item two" in body
        assert "Next Section" not in body

    def test_missing_section_returns_empty(self):
        assert _parse_section("no sections", "Missing") == ""

    def test_section_at_eof(self):
        text = "## Final Section\n- last item\n"
        body = _parse_section(text, "Final Section")
        assert "last item" in body


class TestExtractBulletItems:
    def test_basic_bullets(self):
        text = "- item one\n- item two\nno bullet"
        items = _extract_bullet_items(text)
        assert items == ["- item one", "- item two"]

    def test_empty_text(self):
        assert _extract_bullet_items("") == []

    def test_no_bullets(self):
        assert _extract_bullet_items("just text\nno bullets") == []

    def test_indented_bullets_included(self):
        text = "  - indented bullet\n- normal"
        items = _extract_bullet_items(text)
        assert len(items) == 2


class TestPendingEffortsToBullets:
    def test_basic_conversion(self):
        text = "### Effort A — Deploy to prod\n**State:** ready\n"
        bullets = _pending_efforts_to_bullets(text)
        assert "Deploy to prod" in bullets
        assert bullets.startswith("- **")

    def test_blocked_on_included_when_real_blocker(self):
        text = (
            "### Effort B — Restart bot\n"
            "**State:** waiting\n"
            "**Blocked on:** Moralis cap resets 2026-05-03\n"
        )
        bullets = _pending_efforts_to_bullets(text)
        assert "Moralis" in bullets

    def test_blocked_on_omitted_when_unblocked(self):
        text = (
            "### Effort A — Deploy\n"
            "**State:** ready\n"
            "**Blocked on:** nothing — ready to build\n"
        )
        bullets = _pending_efforts_to_bullets(text)
        assert "blocked" not in bullets.lower()

    def test_multiple_efforts(self):
        text = (
            "### Effort A — First\n**State:** done\n\n"
            "### Effort B — Second\n**State:** pending\n"
        )
        bullets = _pending_efforts_to_bullets(text)
        lines = [l for l in bullets.splitlines() if l.startswith("- ")]
        assert len(lines) == 2

    def test_empty_text_returns_empty(self):
        assert _pending_efforts_to_bullets("") == ""


class TestFirstDoneLabel:
    def test_extracts_bold_label(self):
        text = "- **Phase 5E Auth** — completed the auth module\n- other item"
        label = _first_done_label(text)
        assert label == "Phase 5E Auth"

    def test_falls_back_to_plain_text(self):
        text = "- plain item without bold"
        label = _first_done_label(text)
        assert "plain item" in label

    def test_empty_text_default_label(self):
        assert _first_done_label("") == "session complete"


class TestReplaceSectionBody:
    def test_replaces_body(self):
        status = "## Queued Next Session\n\n- old item\n\n## Other\nstuff\n"
        result = _replace_section_body(status, "Queued Next Session", "- new item")
        assert "new item" in result
        assert "old item" not in result
        assert "Other" in result

    def test_missing_section_unchanged(self):
        status = "## Other\nstuff\n"
        result = _replace_section_body(status, "Queued Next Session", "- new")
        assert result == status


class TestPrependToSection:
    def test_prepends_entry(self):
        status = "## Recent Wins\n\n- old win\n\n## Other\nstuff\n"
        result = _prepend_to_section(status, "Recent Wins", "- new win")
        idx_new = result.index("new win")
        idx_old = result.index("old win")
        assert idx_new < idx_old


class TestUpdateLastUpdatedLine:
    def test_updates_line(self):
        status = "## Last Updated: 2026-01-01 — old label\nmore content\n"
        result = _update_last_updated_line(status, "2026-02-01 — new label")
        assert "2026-02-01 — new label" in result
        assert "2026-01-01" not in result

    def test_missing_line_unchanged(self):
        status = "## Other Section\ncontent\n"
        result = _update_last_updated_line(status, "2026-02-01 — label")
        assert result == status


class TestBuildUpdatedStatus:
    def test_last_updated_changed(self):
        result = _build_updated_status(SAMPLE_HANDOFF, SAMPLE_STATUS)
        assert "Phase 5E Auth" in result
        assert "2026-01-01" not in result.split("\n")[0]  # Last Updated line changed

    def test_queued_section_updated(self):
        result = _build_updated_status(SAMPLE_HANDOFF, SAMPLE_STATUS)
        assert "Deploy to prod" in result
        assert "old queue item" not in result

    def test_recent_wins_prepended(self):
        result = _build_updated_status(SAMPLE_HANDOFF, SAMPLE_STATUS)
        idx_new = result.index("Phase 5E Auth")
        idx_old = result.index("Old win")
        assert idx_new < idx_old

    def test_current_blockers_updated(self):
        result = _build_updated_status(SAMPLE_HANDOFF, SAMPLE_STATUS)
        assert "Moralis cap resets" in result
        assert "old blocker" not in result

    def test_manual_sections_untouched(self):
        result = _build_updated_status(SAMPLE_HANDOFF, SAMPLE_STATUS)
        assert "Shipping Phase 5." in result
