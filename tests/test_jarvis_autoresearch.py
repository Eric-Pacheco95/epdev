"""Pytest tests for tools/scripts/jarvis_autoresearch.py — parse_metrics and extract_section."""

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from unittest.mock import patch
from tools.scripts.jarvis_autoresearch import (
    parse_metrics, extract_section, read_recent_files,
    write_autonomous_signal, read_prior_proposals,
    SIGNAL_THRESHOLD_CONTRADICTIONS, SIGNAL_THRESHOLD_COVERAGE,
    _safe_telos_proposal, _grep_anchor,
    _SAFE_TELOS_FILES, _UNSAFE_CHANGE_VERBS,
)


SAMPLE_RESPONSE = """\
=== ANALYSIS ===
Some analysis text here about contradictions and gaps.

=== METRICS ===
contradiction_count: 3
open_questions: 5
coverage_score: 72.5
staleness_flags: 2
insight_count: 4
proposal_count: 3

=== PROPOSALS ===
1. Do something
2. Do something else
3. Do a third thing
"""


class TestParseMetrics:
    def test_parses_all_metrics(self):
        m = parse_metrics(SAMPLE_RESPONSE)
        assert m["contradiction_count"] == 3
        assert m["open_questions"] == 5
        assert m["coverage_score"] == 72.5
        assert m["staleness_flags"] == 2
        assert m["insight_count"] == 4
        assert m["proposal_count"] == 3

    def test_missing_metrics_section(self):
        m = parse_metrics("No metrics here at all")
        assert m["contradiction_count"] == 0
        assert m["coverage_score"] == 0.0

    def test_partial_metrics(self):
        response = "=== METRICS ===\ncontradiction_count: 7\n=== END ==="
        m = parse_metrics(response)
        assert m["contradiction_count"] == 7
        assert m["open_questions"] == 0  # missing = default

    def test_float_values(self):
        response = "=== METRICS ===\ncoverage_score: 85.3\n"
        m = parse_metrics(response)
        assert m["coverage_score"] == 85.3

    def test_empty_string(self):
        m = parse_metrics("")
        assert all(v == 0 or v == 0.0 for v in m.values())


class TestExtractSection:
    def test_extracts_analysis(self):
        result = extract_section(SAMPLE_RESPONSE, "ANALYSIS")
        assert "contradictions" in result

    def test_extracts_proposals(self):
        result = extract_section(SAMPLE_RESPONSE, "PROPOSALS")
        assert "Do something" in result

    def test_extracts_metrics(self):
        result = extract_section(SAMPLE_RESPONSE, "METRICS")
        assert "contradiction_count" in result

    def test_missing_section(self):
        result = extract_section(SAMPLE_RESPONSE, "NONEXISTENT")
        assert result == ""

    def test_empty_input(self):
        result = extract_section("", "ANYTHING")
        assert result == ""


# ---------------------------------------------------------------------------
# read_recent_files
# ---------------------------------------------------------------------------

class TestReadRecentFiles:
    def test_missing_dir_returns_empty(self, tmp_path):
        result = read_recent_files(tmp_path / "missing", days=7)
        assert result == []

    def test_returns_recent_md_files(self, tmp_path):
        (tmp_path / "recent.md").write_text("content", encoding="utf-8")
        result = read_recent_files(tmp_path, days=7)
        assert len(result) == 1
        assert result[0]["name"] == "recent.md"

    def test_ignores_non_md_files(self, tmp_path):
        (tmp_path / "data.json").write_text("{}", encoding="utf-8")
        (tmp_path / "note.md").write_text("hi", encoding="utf-8")
        result = read_recent_files(tmp_path, days=7)
        assert len(result) == 1

    def test_truncates_long_content(self, tmp_path):
        (tmp_path / "big.md").write_text("x" * 2000, encoding="utf-8")
        result = read_recent_files(tmp_path, days=7)
        assert len(result[0]["content"]) < 2000
        assert "truncated" in result[0]["content"]

    def test_respects_max_files_limit(self, tmp_path):
        for i in range(5):
            (tmp_path / f"file{i}.md").write_text("content", encoding="utf-8")
        result = read_recent_files(tmp_path, days=7, max_files=3)
        assert len(result) == 3


# ---------------------------------------------------------------------------
# write_autonomous_signal
# ---------------------------------------------------------------------------

class TestWriteAutonomousSignal:
    def test_no_signal_when_below_thresholds(self, tmp_path):
        import tools.scripts.jarvis_autoresearch as jar
        with patch.object(jar, "SIGNALS_DIR", tmp_path):
            result = write_autonomous_signal(
                {"contradiction_count": 0, "coverage_score": 100},
                tmp_path / "run-test",
            )
        assert result is False
        assert list(tmp_path.glob("*.md")) == []

    def test_signal_written_when_contradictions_high(self, tmp_path):
        import tools.scripts.jarvis_autoresearch as jar
        with patch.object(jar, "SIGNALS_DIR", tmp_path):
            result = write_autonomous_signal(
                {"contradiction_count": SIGNAL_THRESHOLD_CONTRADICTIONS, "coverage_score": 100},
                tmp_path / "run-test",
            )
        assert result is True
        signals = list(tmp_path.glob("*.md"))
        assert len(signals) == 1

    def test_signal_written_when_coverage_low(self, tmp_path):
        import tools.scripts.jarvis_autoresearch as jar
        with patch.object(jar, "SIGNALS_DIR", tmp_path):
            result = write_autonomous_signal(
                {"contradiction_count": 0, "coverage_score": SIGNAL_THRESHOLD_COVERAGE - 1},
                tmp_path / "run-test",
            )
        assert result is True

    def test_signal_content_mentions_contradictions(self, tmp_path):
        import tools.scripts.jarvis_autoresearch as jar
        with patch.object(jar, "SIGNALS_DIR", tmp_path):
            write_autonomous_signal(
                {"contradiction_count": 5, "coverage_score": 100},
                tmp_path / "run-test",
            )
        signal_file = list(tmp_path.glob("*.md"))[0]
        assert "contradiction" in signal_file.read_text(encoding="utf-8").lower()

    def test_dedup_increments_counter(self, tmp_path):
        import tools.scripts.jarvis_autoresearch as jar
        from datetime import datetime
        today = datetime.now().strftime("%Y-%m-%d")
        # pre-create the first signal file so dedup fires
        (tmp_path / f"{today}_telos-introspection-findings.md").write_text("existing")
        with patch.object(jar, "SIGNALS_DIR", tmp_path):
            write_autonomous_signal(
                {"contradiction_count": SIGNAL_THRESHOLD_CONTRADICTIONS, "coverage_score": 100},
                tmp_path / "run-test",
            )
        files = list(tmp_path.glob("*.md"))
        assert len(files) == 2


# ---------------------------------------------------------------------------
# read_prior_proposals
# ---------------------------------------------------------------------------

class TestReadPriorProposals:
    def test_missing_output_base_returns_empty(self, tmp_path):
        import tools.scripts.jarvis_autoresearch as jar
        with patch.object(jar, "OUTPUT_BASE", tmp_path / "missing"):
            result = read_prior_proposals(days=14)
        assert result == []

    def test_reads_proposals_from_run_dirs(self, tmp_path):
        import tools.scripts.jarvis_autoresearch as jar
        run_dir = tmp_path / "run-001"
        run_dir.mkdir()
        (run_dir / "proposals.md").write_text("proposal content", encoding="utf-8")
        with patch.object(jar, "OUTPUT_BASE", tmp_path):
            result = read_prior_proposals(days=14)
        assert len(result) == 1
        assert result[0]["content"] == "proposal content"

    def test_respects_max_runs_limit(self, tmp_path):
        import tools.scripts.jarvis_autoresearch as jar
        for i in range(5):
            d = tmp_path / f"run-{i:03d}"
            d.mkdir()
            (d / "proposals.md").write_text(f"proposal {i}", encoding="utf-8")
        with patch.object(jar, "OUTPUT_BASE", tmp_path):
            result = read_prior_proposals(days=14, max_runs=3)
        assert len(result) <= 3

    def test_truncates_long_proposals(self, tmp_path):
        import tools.scripts.jarvis_autoresearch as jar
        run_dir = tmp_path / "run-001"
        run_dir.mkdir()
        (run_dir / "proposals.md").write_text("x" * 2000, encoding="utf-8")
        with patch.object(jar, "OUTPUT_BASE", tmp_path):
            result = read_prior_proposals(days=14)
        assert len(result[0]["content"]) <= 1600
        assert "truncated" in result[0]["content"]


# ---------------------------------------------------------------------------
# _safe_telos_proposal
# ---------------------------------------------------------------------------

class TestSafeTelosProposal:
    def _valid_file(self):
        return next(iter(_SAFE_TELOS_FILES))

    def test_known_file_safe_change(self):
        assert _safe_telos_proposal({"file": self._valid_file(), "change": "Append new insight"}) is True

    def test_unknown_file_rejected(self):
        assert _safe_telos_proposal({"file": "unknown.md", "change": "Append text"}) is False

    def test_delete_verb_blocked(self):
        assert _safe_telos_proposal({"file": self._valid_file(), "change": "delete this section"}) is False

    def test_remove_file_verb_blocked(self):
        assert _safe_telos_proposal({"file": self._valid_file(), "change": "remove file entry"}) is False

    def test_create_new_file_blocked(self):
        assert _safe_telos_proposal({"file": self._valid_file(), "change": "create new file for tracking"}) is False

    def test_rename_file_blocked(self):
        assert _safe_telos_proposal({"file": self._valid_file(), "change": "rename file to new name"}) is False

    def test_empty_file_rejected(self):
        assert _safe_telos_proposal({"file": "", "change": "Append text"}) is False

    def test_missing_file_key_rejected(self):
        assert _safe_telos_proposal({"change": "Append text"}) is False


# ---------------------------------------------------------------------------
# _grep_anchor
# ---------------------------------------------------------------------------

class TestGrepAnchor:
    def test_with_phrase_returns_phrase(self):
        result = _grep_anchor('replace old value with "new target phrase"')
        assert result is not None
        assert "new target phrase" in result

    def test_to_phrase_returns_phrase(self):
        result = _grep_anchor('update section to "updated content here"')
        assert result is not None
        assert "updated content" in result

    def test_iso_date_extracted(self):
        result = _grep_anchor("append 2026-04-28 entry to log")
        assert result == "2026-04-28"

    def test_last_date_used_for_append(self):
        result = _grep_anchor("replace 2026-01-01 entry with 2026-04-28 value")
        assert result == "2026-04-28"

    def test_quoted_phrase_fallback(self):
        result = _grep_anchor('"a long enough phrase here for testing"')
        assert result is not None

    def test_empty_string_returns_none(self):
        assert _grep_anchor("") is None

    def test_short_words_only_returns_none(self):
        assert _grep_anchor("a b c d") is None

    def test_three_long_words_returns_words(self):
        result = _grep_anchor("apply append update telos strategy")
        assert result is not None
        assert len(result) > 0
