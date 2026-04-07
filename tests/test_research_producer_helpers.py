"""Tests for research_producer.py -- _domain_to_title and is_static_due."""

from datetime import date
from unittest import mock

from tools.scripts.research_producer import _domain_to_title, is_static_due


# --- _domain_to_title ---

def test_domain_to_title_known_domain():
    result = _domain_to_title("crypto", "bitcoin", 30)
    assert "crypto" in result.lower() or "DeFi" in result or "trading" in result.lower()


def test_domain_to_title_fintech():
    result = _domain_to_title("fintech", "payment", 14)
    assert isinstance(result, str)
    assert len(result) > 10


def test_domain_to_title_unknown_domain():
    result = _domain_to_title("unknown_domain_xyz", "some_keyword", 7)
    assert "unknown_domain_xyz" in result
    assert "some_keyword" in result


def test_domain_to_title_general():
    result = _domain_to_title("general", "guitar", 10)
    assert isinstance(result, str)
    assert len(result) > 10


def test_domain_to_title_all_known_domains():
    """All known domains return non-empty strings."""
    for domain in ["fintech", "ai-infra", "crypto", "security", "general", "automotive"]:
        result = _domain_to_title(domain, "kw", 14)
        assert result and len(result) > 10, f"Empty title for domain {domain}"


# --- is_static_due ---

def _make_topic(slug, domain, interval_days=14):
    return {"slug": slug, "domain": domain, "interval_days": interval_days}


def test_is_static_due_no_prior_state():
    """With empty state and no KB articles, topic is always due."""
    topic = _make_topic("crypto-update", "crypto")
    with mock.patch("tools.scripts.research_producer.latest_article_date", return_value=None):
        assert is_static_due(topic, {}) is True


def test_is_static_due_recent_article():
    """Topic is NOT due if KB has a recent article within interval."""
    topic = _make_topic("crypto-update", "crypto", interval_days=14)
    today_str = date.today().isoformat()
    with mock.patch("tools.scripts.research_producer.latest_article_date_for_slug", return_value=today_str):
        assert is_static_due(topic, {}) is False


def test_is_static_due_stale_article():
    """Topic IS due if the only KB article is older than interval_days."""
    topic = _make_topic("crypto-update", "crypto", interval_days=14)
    old_date = "2020-01-01"
    with mock.patch("tools.scripts.research_producer.latest_article_date", return_value=old_date):
        assert is_static_due(topic, {}) is True


def test_is_static_due_recent_injection():
    """Topic is NOT due if recently injected within interval."""
    topic = _make_topic("crypto-update", "crypto", interval_days=14)
    today_str = date.today().isoformat()
    state = {"topics": {"crypto-update": {"last_injected": today_str}}}
    with mock.patch("tools.scripts.research_producer.latest_article_date", return_value=None):
        assert is_static_due(topic, state) is False
