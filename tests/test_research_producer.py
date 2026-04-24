"""Unit tests for tools/scripts/research_producer.py pure helpers."""

import sys
from datetime import date, timedelta
from pathlib import Path
from unittest import mock

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from tools.scripts.research_producer import (
    _domain_to_title,
    _build_worker_notes,
    is_static_due,
)


class TestDomainToTitle:
    def test_known_domain_fintech(self):
        result = _domain_to_title("fintech", "bank", 30)
        assert "Fintech" in result or "fintech" in result.lower()

    def test_known_domain_crypto(self):
        result = _domain_to_title("crypto", "bitcoin", 14)
        assert "Crypto" in result or "crypto" in result.lower()

    def test_known_domain_security(self):
        result = _domain_to_title("security", "injection", 7)
        assert "security" in result.lower() or "Security" in result

    def test_known_domain_ai_infra(self):
        result = _domain_to_title("ai-infra", "agent", 14)
        assert isinstance(result, str)
        assert len(result) > 0

    def test_unknown_domain_uses_fallback(self):
        result = _domain_to_title("unknown-domain", "some_kw", 10)
        assert "unknown-domain" in result

    def test_general_domain_includes_keyword(self):
        result = _domain_to_title("general", "guitar", 14)
        assert "guitar" in result

    def test_returns_string(self):
        assert isinstance(_domain_to_title("fintech", "payment", 5), str)


class TestBuildWorkerNotes:
    def _make_topic(self, depth="default", **kwargs):
        base = {
            "title": "Test Research Topic",
            "type": "research",
            "depth": depth,
            "domain": "ai-infra",
            "slug": "test-topic",
            "tags": ["agent", "llm"],
        }
        base.update(kwargs)
        return base

    def test_contains_title(self):
        topic = self._make_topic()
        notes = _build_worker_notes(topic)
        assert "Test Research Topic" in notes

    def test_contains_domain(self):
        topic = self._make_topic()
        notes = _build_worker_notes(topic)
        assert "ai-infra" in notes

    def test_contains_slug_in_paths(self):
        topic = self._make_topic()
        notes = _build_worker_notes(topic)
        assert "test-topic" in notes

    def test_quick_depth_sub_questions(self):
        topic = self._make_topic(depth="quick")
        notes = _build_worker_notes(topic)
        assert "2-3" in notes

    def test_default_depth_sub_questions(self):
        topic = self._make_topic(depth="default")
        notes = _build_worker_notes(topic)
        assert "5-7" in notes

    def test_deep_depth_sub_questions(self):
        topic = self._make_topic(depth="deep")
        notes = _build_worker_notes(topic)
        assert "8-12" in notes

    def test_tags_included(self):
        topic = self._make_topic(tags=["test-tag-one", "test-tag-two"])
        notes = _build_worker_notes(topic)
        assert "test-tag-one" in notes
        assert "test-tag-two" in notes

    def test_autonomous_marker_present(self):
        notes = _build_worker_notes(self._make_topic())
        assert "AUTONOMOUS" in notes

    def test_source_reason_included(self):
        topic = self._make_topic(_source="watchlist", _reason="stale coverage")
        notes = _build_worker_notes(topic)
        assert "watchlist" in notes
        assert "stale coverage" in notes


class TestIsStaticDue:
    def _topic(self, slug="test-slug", interval_days=14, domain="nonexistent-domain"):
        return {"slug": slug, "interval_days": interval_days, "domain": domain}

    def test_no_prior_state_is_due(self):
        # No KB articles (nonexistent domain), no prior state → due
        topic = self._topic()
        state = {}
        assert is_static_due(topic, state) is True

    def test_recent_injection_not_due(self):
        topic = self._topic(interval_days=14)
        recent = (date.today() - timedelta(days=5)).isoformat()
        state = {"topics": {"test-slug": {"last_injected": recent}}}
        assert is_static_due(topic, state) is False

    def test_stale_injection_is_due(self):
        topic = self._topic(interval_days=14)
        stale = (date.today() - timedelta(days=20)).isoformat()
        state = {"topics": {"test-slug": {"last_injected": stale}}}
        assert is_static_due(topic, state) is True

    def test_interval_boundary_exact_not_due(self):
        # Exactly at interval - 1 day → not due
        topic = self._topic(interval_days=14)
        recent = (date.today() - timedelta(days=13)).isoformat()
        state = {"topics": {"test-slug": {"last_injected": recent}}}
        assert is_static_due(topic, state) is False

    def test_interval_boundary_at_interval_is_due(self):
        # Exactly at interval → due
        topic = self._topic(interval_days=14)
        at_limit = (date.today() - timedelta(days=14)).isoformat()
        state = {"topics": {"test-slug": {"last_injected": at_limit}}}
        assert is_static_due(topic, state) is True
