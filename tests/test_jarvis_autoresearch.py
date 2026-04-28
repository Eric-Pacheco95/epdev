"""Pytest tests for tools/scripts/jarvis_autoresearch.py — parse_metrics and extract_section."""

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from tools.scripts.jarvis_autoresearch import parse_metrics, extract_section, read_recent_files


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
