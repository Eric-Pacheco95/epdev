"""Tests for research_producer._build_worker_notes pure function."""

from tools.scripts.research_producer import _build_worker_notes


def _make_topic(slug, domain, depth="default", title="Test Topic", topic_type="general"):
    return {
        "slug": slug,
        "domain": domain,
        "depth": depth,
        "title": title,
        "type": topic_type,
        "_source": "watchlist",
        "_reason": "test reason",
        "tags": ["tag1", "tag2"],
    }


def test_build_worker_notes_contains_title():
    topic = _make_topic("crypto-update", "crypto", title="Crypto Market Outlook")
    notes = _build_worker_notes(topic)
    assert "Crypto Market Outlook" in notes


def test_build_worker_notes_contains_domain():
    topic = _make_topic("ai-agent-frameworks", "ai-infra")
    notes = _build_worker_notes(topic)
    assert "ai-infra" in notes


def test_build_worker_notes_depth_quick():
    topic = _make_topic("crypto-update", "crypto", depth="quick")
    notes = _build_worker_notes(topic)
    assert "2-3" in notes


def test_build_worker_notes_depth_default():
    topic = _make_topic("crypto-update", "crypto", depth="default")
    notes = _build_worker_notes(topic)
    assert "5-7" in notes


def test_build_worker_notes_depth_deep():
    topic = _make_topic("crypto-update", "crypto", depth="deep")
    notes = _build_worker_notes(topic)
    assert "8-12" in notes


def test_build_worker_notes_output_paths():
    topic = _make_topic("my-slug", "fintech")
    notes = _build_worker_notes(topic)
    assert "memory/work/my-slug/research_brief.md" in notes
    assert "memory/knowledge/fintech/" in notes


def test_build_worker_notes_tags_listed():
    topic = _make_topic("x", "crypto", title="T")
    notes = _build_worker_notes(topic)
    assert "tag1" in notes
    assert "tag2" in notes


def test_build_worker_notes_autonomous_header():
    topic = _make_topic("x", "y")
    notes = _build_worker_notes(topic)
    assert "AUTONOMOUS RESEARCH TASK" in notes
