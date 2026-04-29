"""Tests for tools/scripts/lib/task_proposals.py."""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from tools.scripts.lib.task_proposals import validate_proposal, count_by_status


class TestValidateProposal:
    def test_valid_minimal(self):
        errs = validate_proposal({"title": "Fix bug", "rationale": "signal X"})
        assert errs == []

    def test_missing_title(self):
        errs = validate_proposal({"rationale": "signal X"})
        assert any("title" in e for e in errs)

    def test_empty_title(self):
        errs = validate_proposal({"title": "  ", "rationale": "signal X"})
        assert any("title" in e for e in errs)

    def test_non_string_title(self):
        errs = validate_proposal({"title": 42, "rationale": "signal X"})
        assert any("title" in e for e in errs)

    def test_missing_rationale(self):
        errs = validate_proposal({"title": "Fix bug"})
        assert any("rationale" in e for e in errs)

    def test_empty_rationale(self):
        errs = validate_proposal({"title": "Fix bug", "rationale": ""})
        assert any("rationale" in e for e in errs)

    def test_non_string_source_flagged(self):
        errs = validate_proposal({"title": "Fix", "rationale": "reason", "source": 123})
        assert any("source" in e for e in errs)

    def test_string_source_ok(self):
        errs = validate_proposal({"title": "Fix", "rationale": "reason", "source": "manual"})
        assert errs == []

    def test_suggested_task_dict_ok(self):
        errs = validate_proposal({
            "title": "Fix", "rationale": "reason",
            "suggested_task": {"priority": "high"}
        })
        assert errs == []

    def test_suggested_task_non_dict_flagged(self):
        errs = validate_proposal({
            "title": "Fix", "rationale": "reason",
            "suggested_task": "should be dict"
        })
        assert any("suggested_task" in e for e in errs)

    def test_none_suggested_task_ok(self):
        errs = validate_proposal({"title": "Fix", "rationale": "reason", "suggested_task": None})
        assert errs == []

    def test_multiple_errors_returned(self):
        errs = validate_proposal({})
        assert len(errs) >= 2  # missing both title and rationale


class TestCountByStatus:
    def test_empty_file_returns_empty(self, tmp_path):
        f = tmp_path / "proposals.jsonl"
        f.write_text("", encoding="utf-8")
        assert count_by_status(f) == {}

    def test_missing_file_returns_empty(self, tmp_path):
        assert count_by_status(tmp_path / "nonexistent.jsonl") == {}

    def test_counts_single_status(self, tmp_path):
        f = tmp_path / "proposals.jsonl"
        rows = [{"status": "pending"}, {"status": "pending"}]
        f.write_text("\n".join(json.dumps(r) for r in rows) + "\n", encoding="utf-8")
        assert count_by_status(f) == {"pending": 2}

    def test_counts_multiple_statuses(self, tmp_path):
        f = tmp_path / "proposals.jsonl"
        rows = [
            {"status": "pending"},
            {"status": "approved"},
            {"status": "approved"},
            {"status": "rejected"},
        ]
        f.write_text("\n".join(json.dumps(r) for r in rows) + "\n", encoding="utf-8")
        result = count_by_status(f)
        assert result == {"pending": 1, "approved": 2, "rejected": 1}

    def test_missing_status_counted_as_unknown(self, tmp_path):
        f = tmp_path / "proposals.jsonl"
        f.write_text(json.dumps({"title": "no status"}) + "\n", encoding="utf-8")
        result = count_by_status(f)
        assert result == {"unknown": 1}

    def test_skips_invalid_json_lines(self, tmp_path):
        f = tmp_path / "proposals.jsonl"
        f.write_text('not_json\n{"status": "pending"}\n', encoding="utf-8")
        result = count_by_status(f)
        assert result == {"pending": 1}

    def test_skips_blank_lines(self, tmp_path):
        f = tmp_path / "proposals.jsonl"
        f.write_text('\n\n{"status": "pending"}\n\n', encoding="utf-8")
        result = count_by_status(f)
        assert result == {"pending": 1}
