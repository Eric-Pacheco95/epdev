"""Tests for tools/scripts/sync_handoff.py pure helper functions."""
import sys
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import tools.scripts.sync_handoff as sh


# ---------------------------------------------------------------------------
# parse_pending
# ---------------------------------------------------------------------------

SAMPLE_HANDOFF = """\
# Handoff

## Done This Session
- shipped thing

## Pending Efforts

### Effort A — deploy router
**State:** ready
**Blocked on:** nothing

### Effort B — write tests
**State:** in progress

## Hard Constraints
- memory cap
"""


def test_parse_pending_finds_all_efforts():
    efforts = sh.parse_pending(SAMPLE_HANDOFF)
    assert len(efforts) == 2


def test_parse_pending_titles():
    efforts = sh.parse_pending(SAMPLE_HANDOFF)
    assert efforts[0]["title"] == "Effort A — deploy router"
    assert efforts[1]["title"] == "Effort B — write tests"


def test_parse_pending_body_content():
    efforts = sh.parse_pending(SAMPLE_HANDOFF)
    assert "ready" in efforts[0]["body"]


def test_parse_pending_no_section_returns_empty():
    result = sh.parse_pending("# just some text\n\n## Done\n- yep\n")
    assert result == []


def test_parse_pending_stops_at_next_h2():
    efforts = sh.parse_pending(SAMPLE_HANDOFF)
    # Hard Constraints should not bleed into the body of Effort B
    assert "memory cap" not in efforts[1]["body"]


def test_parse_pending_empty_section():
    doc = "## Pending Efforts\n\n## Next Section\nfoo\n"
    assert sh.parse_pending(doc) == []


# ---------------------------------------------------------------------------
# extract_keywords
# ---------------------------------------------------------------------------

def test_extract_keywords_filters_stopwords():
    kws = sh.extract_keywords("Effort A — fix the session router")
    assert "the" not in kws
    assert "session" not in kws  # "session" is a stopword


def test_extract_keywords_keeps_distinctive_tokens():
    kws = sh.extract_keywords("Effort A — deploy router")
    assert "deploy" in kws
    assert "router" in kws


def test_extract_keywords_short_tokens_excluded():
    # tokens < 3 chars are excluded by the regex [A-Za-z][A-Za-z0-9\-_]{2,}
    kws = sh.extract_keywords("do it")
    assert "do" not in kws
    assert "it" not in kws


def test_extract_keywords_returns_all_non_stopword_tokens():
    # extract_keywords returns all distinctive tokens; caller slices to 5
    title = "alpha bravo charlie delta epsilon foxtrot"
    kws = sh.extract_keywords(title)
    assert "alpha" in kws and "foxtrot" in kws


def test_extract_keywords_empty_title():
    assert sh.extract_keywords("") == []


# ---------------------------------------------------------------------------
# classify
# ---------------------------------------------------------------------------

def test_classify_done_when_path_and_keyword_overlap():
    path_hits = {"foo.py": [("abc1234", "deploy router")]}
    keyword_hits = {"deploy": [("abc1234", "deploy router")]}
    assert sh.classify(path_hits, keyword_hits) == "DONE"


def test_classify_likely_done_when_path_only():
    path_hits = {"foo.py": [("abc1234", "deploy router")]}
    keyword_hits = {"deploy": []}
    assert sh.classify(path_hits, keyword_hits) == "LIKELY-DONE"


def test_classify_keyword_hit_when_no_path_but_keyword():
    path_hits = {}
    keyword_hits = {"router": [("abc1234", "refactor router")]}
    assert sh.classify(path_hits, keyword_hits) == "KEYWORD-HIT"


def test_classify_pending_when_nothing():
    assert sh.classify({}, {}) == "PENDING"
    assert sh.classify({"foo.py": []}, {"kw": []}) == "PENDING"


# ---------------------------------------------------------------------------
# render
# ---------------------------------------------------------------------------

SAMPLE_STATE = {
    "handoff": "data/session_handoff_test.md",
    "handoff_mtime": "2026-04-28T02:00:00+00:00",
    "cutoff": "2026-04-26T02:00:00+00:00",
    "lookback_hours": 48,
    "effort_count": 1,
    "efforts": [
        {
            "title": "Effort A — deploy router",
            "paths": ["tools/scripts/overnight_runner.py"],
            "keywords": ["deploy", "router"],
            "referenced_commits": [],
            "verdict": "DONE",
            "path_commits": [{"hash": "abc1234", "subject": "deploy router fix"}],
            "keyword_only_commits": [],
        }
    ],
}


def test_render_shows_handoff_path():
    out = sh.render(SAMPLE_STATE)
    assert "session_handoff_test.md" in out


def test_render_shows_verdict():
    out = sh.render(SAMPLE_STATE)
    assert "DONE" in out


def test_render_shows_effort_title():
    out = sh.render(SAMPLE_STATE)
    assert "Effort A — deploy router" in out


def test_render_shows_commit_hash():
    out = sh.render(SAMPLE_STATE)
    assert "abc1234" in out


def test_render_empty_efforts():
    state = dict(SAMPLE_STATE, effort_count=0)
    out = sh.render(state)
    assert "no" in out.lower()


def test_render_keyword_only_commits_shown():
    state = dict(SAMPLE_STATE)
    state["efforts"] = [
        {
            "title": "Effort B",
            "paths": [],
            "keywords": ["refactor"],
            "referenced_commits": [],
            "verdict": "KEYWORD-HIT",
            "path_commits": [],
            "keyword_only_commits": [{"hash": "xyz9999", "subject": "refactor something"}],
        }
    ]
    out = sh.render(state)
    assert "xyz9999" in out


def test_render_no_commits_says_so():
    state = dict(SAMPLE_STATE)
    state["efforts"] = [
        {
            "title": "Effort C",
            "paths": [],
            "keywords": [],
            "referenced_commits": [],
            "verdict": "PENDING",
            "path_commits": [],
            "keyword_only_commits": [],
        }
    ]
    out = sh.render(state)
    assert "No candidate" in out
