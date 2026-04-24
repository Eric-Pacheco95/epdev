"""Unit tests for tools/scripts/corpus_extractor.py pure helpers."""

import sys
import tempfile
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

import pytest
from tools.scripts.corpus_extractor import (
    count_keywords,
    overlap_terms,
    _normalize_pending_entry,
    vtt_to_text,
    KEYWORDS,
    STOPWORDS,
)


class TestCountKeywords:
    def test_agent_detected(self):
        result = count_keywords("AI agents are helpful for agent orchestration")
        assert result["agent"] >= 2

    def test_llm_singular_and_plural(self):
        result = count_keywords("LLM inference and LLMs in production")
        assert result["llm"] == 2

    def test_no_match_returns_zero(self):
        result = count_keywords("hello world, nothing here")
        assert result["agent"] == 0
        assert result["claude"] == 0

    def test_all_keywords_present_in_output(self):
        result = count_keywords("")
        for key in KEYWORDS:
            assert key in result

    def test_case_insensitive(self):
        result = count_keywords("CLAUDE claude Claude")
        assert result["claude"] == 3

    def test_mcp_full_name(self):
        result = count_keywords("The Model Context Protocol is important")
        assert result["mcp"] >= 1


class TestOverlapTerms:
    def test_returns_list_of_tuples(self):
        text = "agent agent agent harness harness harness orchestration"
        corpus = "agent harness orchestration"
        result = overlap_terms(text, corpus, top_n=5)
        assert isinstance(result, list)
        if result:
            assert isinstance(result[0], tuple)
            assert len(result[0]) == 2

    def test_respects_top_n(self):
        # Make many unique terms appear >= 3 times
        words = ["alpha", "bravo", "charlie", "delta", "echo", "foxtrot"]
        text = " ".join(w for w in words for _ in range(3))
        corpus = " ".join(words)
        result = overlap_terms(text, corpus, top_n=2)
        assert len(result) <= 2

    def test_stopwords_excluded(self):
        # "the", "and" are stopwords; they should not appear in results
        text = " ".join(["the"] * 10 + ["and"] * 10)
        corpus = "the and"
        result = overlap_terms(text, corpus, top_n=20)
        terms = [t for t, _ in result]
        assert "the" not in terms
        assert "and" not in terms

    def test_term_must_appear_in_corpus(self):
        text = "agent agent agent harness harness harness"
        corpus = "agent"  # harness NOT in corpus
        result = overlap_terms(text, corpus, top_n=20)
        terms = [t for t, _ in result]
        assert "harness" not in terms

    def test_minimum_count_filter(self):
        # Terms appearing < 3 times should be excluded
        text = "unique_term_xyz unique_term_xyz"  # only 2 appearances
        corpus = "unique_term_xyz"
        result = overlap_terms(text, corpus, top_n=20)
        terms = [t for t, _ in result]
        assert "unique_term_xyz" not in terms

    def test_empty_text_returns_empty(self):
        result = overlap_terms("", "some corpus text", top_n=5)
        assert result == []


class TestNormalizePendingEntry:
    def test_string_entry(self):
        vid_id, meta = _normalize_pending_entry("abc123")
        assert vid_id == "abc123"
        assert meta is None

    def test_dict_with_id(self):
        entry = {"id": "xyz789", "title": "Test Video", "priority": 5}
        vid_id, meta = _normalize_pending_entry(entry)
        assert vid_id == "xyz789"
        assert meta == entry

    def test_dict_id_converted_to_str(self):
        entry = {"id": 42, "title": "Numeric ID"}
        vid_id, meta = _normalize_pending_entry(entry)
        assert vid_id == "42"
        assert isinstance(vid_id, str)

    def test_dict_without_id_raises(self):
        with pytest.raises(ValueError):
            _normalize_pending_entry({"title": "No ID"})

    def test_invalid_type_raises(self):
        with pytest.raises(ValueError):
            _normalize_pending_entry(12345)

    def test_list_raises(self):
        with pytest.raises(ValueError):
            _normalize_pending_entry(["a", "b"])


class TestVttToText:
    def test_strips_timestamps_and_tags(self):
        vtt_content = (
            "WEBVTT\n\n"
            "00:00:01.000 --> 00:00:04.000\n"
            "Hello <c>world</c>\n\n"
            "00:00:05.000 --> 00:00:08.000\n"
            "This is a test\n"
        )
        with tempfile.NamedTemporaryFile(mode="w", suffix=".vtt", delete=False, encoding="utf-8") as f:
            f.write(vtt_content)
            tmp = Path(f.name)
        try:
            result = vtt_to_text(tmp)
            assert "Hello" in result
            assert "world" in result
            assert "This is a test" in result
            assert "-->" not in result
            assert "WEBVTT" not in result
            assert "<c>" not in result
        finally:
            tmp.unlink()

    def test_deduplicates_repeated_lines(self):
        vtt_content = (
            "WEBVTT\n\n"
            "00:00:01.000 --> 00:00:02.000\n"
            "Repeated line\n\n"
            "00:00:02.000 --> 00:00:03.000\n"
            "Repeated line\n"
        )
        with tempfile.NamedTemporaryFile(mode="w", suffix=".vtt", delete=False, encoding="utf-8") as f:
            f.write(vtt_content)
            tmp = Path(f.name)
        try:
            result = vtt_to_text(tmp)
            # Should appear only once due to deduplication
            assert result.count("Repeated line") == 1
        finally:
            tmp.unlink()
