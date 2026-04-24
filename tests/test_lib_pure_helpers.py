"""Unit tests for pure helpers in tools/scripts/lib/ modules."""

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from tools.scripts.lib.task_proposals import validate_proposal
from tools.scripts.lib.worktree import _exclude_file_has_line


class TestValidateProposal:
    def _valid(self, **overrides):
        rec = {"title": "Add feature X", "rationale": "Needed for Y", "source": "test"}
        rec.update(overrides)
        return rec

    def test_valid_record_no_errors(self):
        assert validate_proposal(self._valid()) == []

    def test_missing_title_error(self):
        rec = self._valid()
        del rec["title"]
        errs = validate_proposal(rec)
        assert any("title" in e for e in errs)

    def test_empty_title_error(self):
        errs = validate_proposal(self._valid(title="   "))
        assert any("title" in e for e in errs)

    def test_missing_rationale_error(self):
        rec = self._valid()
        del rec["rationale"]
        errs = validate_proposal(rec)
        assert any("rationale" in e for e in errs)

    def test_non_string_source_error(self):
        errs = validate_proposal(self._valid(source=123))
        assert any("source" in e for e in errs)

    def test_string_source_ok(self):
        assert validate_proposal(self._valid(source="autonomous")) == []

    def test_suggested_task_dict_ok(self):
        assert validate_proposal(self._valid(suggested_task={"type": "build"})) == []

    def test_suggested_task_non_dict_error(self):
        errs = validate_proposal(self._valid(suggested_task="not-a-dict"))
        assert any("suggested_task" in e for e in errs)

    def test_suggested_task_none_ok(self):
        assert validate_proposal(self._valid(suggested_task=None)) == []

    def test_multiple_errors_returned(self):
        errs = validate_proposal({})
        assert len(errs) >= 2  # title + rationale both missing


class TestExcludeFileHasLine:
    def test_exact_match(self):
        existing = "/memory/learning/signals\n/memory/learning/signals/\n"
        assert _exclude_file_has_line(existing, "/memory/learning/signals") is True

    def test_no_match(self):
        existing = "/data\n/logs\n"
        assert _exclude_file_has_line(existing, "/memory") is False

    def test_comment_line_ignored(self):
        existing = "# /memory/learning/signals\n"
        assert _exclude_file_has_line(existing, "/memory/learning/signals") is False

    def test_empty_string(self):
        assert _exclude_file_has_line("", "/memory") is False

    def test_empty_lines_skipped(self):
        existing = "\n\n/data\n\n"
        assert _exclude_file_has_line(existing, "/data") is True
        assert _exclude_file_has_line(existing, "") is False

    def test_exact_match_required_not_prefix(self):
        # "/memory" should NOT match "/memory/learning"
        existing = "/memory/learning\n"
        assert _exclude_file_has_line(existing, "/memory") is False

    def test_whitespace_stripped(self):
        # Leading/trailing spaces on the stored line should still match
        existing = "  /data/logs  \n"
        assert _exclude_file_has_line(existing, "/data/logs") is True

    def test_multiple_patterns_one_matches(self):
        existing = "/data\n/logs\n/memory\n"
        assert _exclude_file_has_line(existing, "/logs") is True
        assert _exclude_file_has_line(existing, "/other") is False
