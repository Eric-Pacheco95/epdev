"""Tests for prediction_event_generator.py -- deterministic logic only (no claude calls)."""

import json
import tempfile
from pathlib import Path

import pytest
import yaml

from tools.scripts.prediction_event_generator import (
    compute_domain_gaps,
    extract_existing_events_context,
    parse_proposed_events,
    append_events_to_yaml,
    TARGET_PER_DOMAIN,
    VALID_DOMAINS,
)


# ---------------------------------------------------------------------------
# compute_domain_gaps
# ---------------------------------------------------------------------------

class TestComputeDomainGaps:
    def test_empty_events_all_gaps(self):
        gaps = compute_domain_gaps([], {})
        for domain in VALID_DOMAINS:
            assert gaps[domain] == TARGET_PER_DOMAIN

    def test_some_events_reduce_gap(self):
        events = [
            {"event_id": "geo-1", "domain": "geopolitics"},
            {"event_id": "geo-2", "domain": "geopolitics"},
            {"event_id": "mkt-1", "domain": "market"},
        ]
        gaps = compute_domain_gaps(events, {})
        assert gaps["geopolitics"] == TARGET_PER_DOMAIN - 2
        assert gaps["market"] == TARGET_PER_DOMAIN - 1
        assert gaps["technology"] == TARGET_PER_DOMAIN
        assert gaps["planning"] == TARGET_PER_DOMAIN

    def test_at_target_not_in_gaps(self):
        events = [{"event_id": f"geo-{i}", "domain": "geopolitics"} for i in range(TARGET_PER_DOMAIN)]
        gaps = compute_domain_gaps(events, {})
        assert "geopolitics" not in gaps
        assert "market" in gaps

    def test_over_target_not_in_gaps(self):
        events = [{"event_id": f"geo-{i}", "domain": "geopolitics"} for i in range(TARGET_PER_DOMAIN + 5)]
        gaps = compute_domain_gaps(events, {})
        assert "geopolitics" not in gaps

    def test_proposed_events_count_toward_target(self):
        """Proposed events should count so we don't over-propose."""
        events = [
            {"event_id": f"geo-{i}", "domain": "geopolitics", "status": "proposed"}
            for i in range(10)
        ]
        gaps = compute_domain_gaps(events, {})
        assert gaps["geopolitics"] == TARGET_PER_DOMAIN - 10


# ---------------------------------------------------------------------------
# parse_proposed_events
# ---------------------------------------------------------------------------

class TestParseProposedEvents:
    def test_valid_yaml_list(self):
        yaml_str = """
- event_id: "plan-career-change-2019"
  description: "Will remote work become the default for tech companies by 2021?"
  domain: planning
  knowledge_cutoff_date: "2019-06-01"
  known_outcome: "COVID-19 forced remote work adoption in 2020, becoming semi-permanent"
  difficulty: high
  at_time_context: >
    Remote work is growing but still minority. WeWork valued at $47B.
"""
        events = parse_proposed_events(yaml_str)
        assert len(events) == 1
        assert events[0]["event_id"] == "plan-career-change-2019"
        assert events[0]["domain"] == "planning"
        assert events[0]["status"] == "approved"

    def test_rejects_post_2022_events(self):
        yaml_str = """
- event_id: "tech-chatgpt-2023"
  description: "Will ChatGPT reach 100M users?"
  domain: technology
  knowledge_cutoff_date: "2023-01-01"
  known_outcome: "Yes"
  difficulty: low
  at_time_context: "ChatGPT launched Nov 2022"
"""
        events = parse_proposed_events(yaml_str)
        assert len(events) == 0

    def test_rejects_invalid_domain(self):
        yaml_str = """
- event_id: "sports-1"
  description: "Who wins?"
  domain: sports
  knowledge_cutoff_date: "2020-01-01"
  known_outcome: "Team A"
  difficulty: low
  at_time_context: "Context"
"""
        events = parse_proposed_events(yaml_str)
        assert len(events) == 0

    def test_strips_markdown_fencing(self):
        yaml_str = """```yaml
- event_id: "geo-test"
  description: "Test event"
  domain: geopolitics
  knowledge_cutoff_date: "2020-01-01"
  known_outcome: "Outcome"
  difficulty: medium
  at_time_context: "Context here"
```"""
        events = parse_proposed_events(yaml_str)
        assert len(events) == 1

    def test_missing_required_fields(self):
        yaml_str = """
- event_id: "incomplete"
  description: "Missing fields"
"""
        events = parse_proposed_events(yaml_str)
        assert len(events) == 0

    def test_forces_approved_status(self):
        """Auto-approve: all generated events get status=approved regardless of input."""
        yaml_str = """
- event_id: "geo-test"
  description: "Test"
  domain: geopolitics
  knowledge_cutoff_date: "2020-01-01"
  known_outcome: "Outcome"
  difficulty: medium
  status: proposed
  at_time_context: "Context"
"""
        events = parse_proposed_events(yaml_str)
        assert len(events) == 1
        assert events[0]["status"] == "approved"


# ---------------------------------------------------------------------------
# append_events_to_yaml
# ---------------------------------------------------------------------------

class TestAppendEventsToYaml:
    def test_deduplicates_by_event_id(self):
        existing = [{"event_id": "geo-1", "domain": "geopolitics"}]
        new_events = [
            {"event_id": "geo-1", "domain": "geopolitics", "description": "dup",
             "knowledge_cutoff_date": "2020-01-01", "known_outcome": "x",
             "difficulty": "low", "status": "proposed", "at_time_context": "ctx"},
            {"event_id": "geo-2", "domain": "geopolitics", "description": "new",
             "knowledge_cutoff_date": "2020-01-01", "known_outcome": "y",
             "difficulty": "low", "status": "proposed", "at_time_context": "ctx"},
        ]
        # Use a temp file to avoid touching real data
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False, encoding="utf-8") as f:
            yaml.dump({"events": existing}, f)
            tmp_path = Path(f.name)

        # Monkey-patch EVENTS_FILE for this test
        import tools.scripts.prediction_event_generator as mod
        orig = mod.EVENTS_FILE
        mod.EVENTS_FILE = tmp_path
        try:
            added = append_events_to_yaml(new_events, existing)
            assert added == 1  # geo-1 deduped, geo-2 added
        finally:
            mod.EVENTS_FILE = orig
            tmp_path.unlink(missing_ok=True)


# ---------------------------------------------------------------------------
# extract_existing_events_context
# ---------------------------------------------------------------------------

class TestExtractContext:
    def test_empty_events(self):
        assert extract_existing_events_context([]) == "No existing events."

    def test_formats_events(self):
        events = [{"event_id": "geo-1", "description": "Will X happen?", "domain": "geopolitics"}]
        ctx = extract_existing_events_context(events)
        assert "geo-1" in ctx
        assert "geopolitics" in ctx
