"""Tests for tools/scripts/sync_handoff.py."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from tools.scripts.sync_handoff import (
    parse_pending,
    extract_keywords,
    classify,
    render,
    STOPWORDS,
    LOOKBACK_HOURS,
)


SAMPLE_HANDOFF = (
    "# Session Handoff\n\n"
    "## Done This Session\n- task A\n\n"
    "## Pending Efforts\n\n"
    "### #1 — Implement authentication\nState: ready\n`tools/scripts/auth.py`\n\n"
    "### #2 — Refactor database layer\nRewrite the DB connection pooling.\n\n"
    "## Quick Start\nrun effort #1 first.\n"
)


class TestParsePending:
    def test_two_efforts_parsed(self):
        efforts = parse_pending(SAMPLE_HANDOFF)
        assert len(efforts) == 2

    def test_effort_titles(self):
        efforts = parse_pending(SAMPLE_HANDOFF)
        assert efforts[0]["title"] == "#1 — Implement authentication"
        assert efforts[1]["title"] == "#2 — Refactor database layer"

    def test_effort_body_content(self):
        efforts = parse_pending(SAMPLE_HANDOFF)
        assert "auth.py" in efforts[0]["body"]

    def test_no_section_returns_empty(self):
        assert parse_pending("# Just a title\nno pending section") == []

    def test_empty_section_returns_empty(self):
        text = "## Pending Efforts\n\n## Next Section\nstuff"
        assert parse_pending(text) == []

    def test_section_stops_at_next_h2(self):
        text = (
            "## Pending Efforts\n\n### effort one\nbody\n\n"
            "## Quick Start\n### not an effort\n"
        )
        efforts = parse_pending(text)
        assert len(efforts) == 1
        assert efforts[0]["title"] == "effort one"

    def test_case_insensitive_header(self):
        text = "## pending efforts\n\n### effort one\nbody\n"
        assert len(parse_pending(text)) == 1


class TestExtractKeywords:
    def test_removes_stopwords(self):
        kws = extract_keywords("Fix the database and update the schema")
        assert "the" not in kws
        assert "and" not in kws

    def test_keeps_distinctive_words(self):
        kws = extract_keywords("Implement authentication refactoring")
        assert "Implement" in kws
        assert "authentication" in kws

    def test_short_tokens_filtered(self):
        kws = extract_keywords("Do it")
        # "Do" is 2 chars, filtered; "it" is in stopwords
        assert kws == []

    def test_returns_list(self):
        assert isinstance(extract_keywords("some keywords here"), list)

    def test_skill_is_stopword(self):
        kws = extract_keywords("add skill to pipeline")
        assert "skill" not in kws


class TestClassify:
    def test_path_and_keyword_hit_is_done(self):
        path_hits = {"file.py": [("abc1234", "feat: update file")]}
        keyword_hits = {"update": [("abc1234", "feat: update file")]}
        assert classify(path_hits, keyword_hits) == "DONE"

    def test_path_hit_no_keyword_is_likely_done(self):
        path_hits = {"file.py": [("abc1234", "feat: update file")]}
        keyword_hits = {"something": [("def5678", "other commit")]}
        assert classify(path_hits, keyword_hits) == "LIKELY-DONE"

    def test_keyword_only_is_keyword_hit(self):
        path_hits = {}
        keyword_hits = {"implement": [("abc1234", "feat: implement something")]}
        assert classify(path_hits, keyword_hits) == "KEYWORD-HIT"

    def test_no_hits_is_pending(self):
        assert classify({}, {}) == "PENDING"

    def test_empty_path_hits_empty_keyword_hits(self):
        path_hits = {"file.py": []}
        keyword_hits = {"word": []}
        assert classify(path_hits, keyword_hits) == "PENDING"


class TestRender:
    def test_no_efforts_message(self):
        state = {
            "handoff": "data/handoff.md",
            "handoff_mtime": "2026-01-01T00:00:00+00:00",
            "cutoff": "2025-12-30T00:00:00+00:00",
            "lookback_hours": 48,
            "effort_count": 0,
            "efforts": [],
        }
        msg = render(state)
        assert "no '## Pending Efforts'" in msg

    def test_efforts_listed(self):
        state = {
            "handoff": "data/handoff.md",
            "handoff_mtime": "2026-01-01T00:00:00+00:00",
            "cutoff": "2025-12-30T00:00:00+00:00",
            "lookback_hours": 48,
            "effort_count": 1,
            "efforts": [{
                "title": "test effort",
                "verdict": "PENDING",
                "paths": [],
                "keywords": ["effort"],
                "referenced_commits": [],
                "path_commits": [],
                "keyword_only_commits": [],
            }],
        }
        msg = render(state)
        assert "test effort" in msg
        assert "PENDING" in msg

    def test_path_commits_shown(self):
        state = {
            "handoff": "data/handoff.md",
            "handoff_mtime": "2026-01-01T00:00:00+00:00",
            "cutoff": "2025-12-30T00:00:00+00:00",
            "lookback_hours": 48,
            "effort_count": 1,
            "efforts": [{
                "title": "effort",
                "verdict": "DONE",
                "paths": ["tools/scripts/foo.py"],
                "keywords": ["effort"],
                "referenced_commits": [],
                "path_commits": [{"hash": "abc1234", "subject": "feat: done it"}],
                "keyword_only_commits": [],
            }],
        }
        msg = render(state)
        assert "abc1234" in msg
        assert "done it" in msg


class TestConstants:
    def test_lookback_hours(self):
        assert LOOKBACK_HOURS == 48

    def test_stopwords_populated(self):
        assert len(STOPWORDS) > 10
        assert "the" in STOPWORDS
