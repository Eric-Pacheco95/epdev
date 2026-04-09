"""Tests for prediction_backtest_producer.py -- pure helper functions."""
from __future__ import annotations

import json
import tempfile
from pathlib import Path

import pytest
import yaml

from tools.scripts.prediction_backtest_producer import (
    build_prompt,
    extract_primary_confidence,
    load_events,
    score_prediction,
    select_unrun_events,
    write_prediction_file,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

SAMPLE_EVENT = {
    "event_id": "test-btc-2021",
    "description": "Will Bitcoin reach $60,000 by end of 2021?",
    "domain": "market",
    "knowledge_cutoff_date": "2021-10-01",
    "known_outcome": "Bitcoin reached $69,044 on November 10 2021.",
    "difficulty": "medium",
    "at_time_context": "Bitcoin at $47,000. Previous ATH $64,895 in April.",
}


# ---------------------------------------------------------------------------
# build_prompt
# ---------------------------------------------------------------------------

def test_build_prompt_contains_cutoff_date():
    prompt = build_prompt(SAMPLE_EVENT)
    assert "2021-10-01" in prompt


def test_build_prompt_contains_description():
    prompt = build_prompt(SAMPLE_EVENT)
    assert "Will Bitcoin reach $60,000" in prompt


def test_build_prompt_contains_context():
    prompt = build_prompt(SAMPLE_EVENT)
    assert "Bitcoin at $47,000" in prompt


def test_build_prompt_contains_backtesting_header():
    prompt = build_prompt(SAMPLE_EVENT)
    assert "BACKTESTING MODE" in prompt


def test_build_prompt_repeats_date_as_constraint():
    prompt = build_prompt(SAMPLE_EVENT)
    # Should mention the date at least twice (instruction + context)
    assert prompt.count("2021-10-01") >= 2


# ---------------------------------------------------------------------------
# extract_primary_confidence
# ---------------------------------------------------------------------------

def test_extract_confidence_basic():
    output = "## Primary Prediction\nI predict Bitcoin reaches $60K with 65% confidence."
    conf = extract_primary_confidence(output)
    assert conf is not None
    assert abs(conf - 0.65) < 0.01


def test_extract_confidence_no_primary_section():
    output = "Outcomes:\n1. Yes -- 70%\n2. No -- 30%"
    conf = extract_primary_confidence(output)
    assert conf is not None
    assert conf == 0.70  # highest


def test_extract_confidence_returns_none_when_no_percentage():
    output = "I think it will probably go up but I cannot say for sure."
    conf = extract_primary_confidence(output)
    assert conf is None


def test_extract_confidence_clamps_to_valid_range():
    output = "## Primary Prediction\nAbsolutely certain 100% probability."
    conf = extract_primary_confidence(output)
    assert conf is not None
    assert 0.0 < conf <= 1.0


# ---------------------------------------------------------------------------
# score_prediction
# ---------------------------------------------------------------------------

def test_score_no_leakage_flag_normal_confidence():
    output = "## Primary Prediction\nBitcoin reaches target with 70% probability."
    scoring = score_prediction(SAMPLE_EVENT, output)
    assert scoring["suspect_leakage"] is False
    assert scoring["leakage_flag"] == ""


def test_score_flags_suspect_leakage_high_confidence():
    output = "## Primary Prediction\nI am 90% certain Bitcoin reaches $60K."
    scoring = score_prediction(SAMPLE_EVENT, output)
    assert scoring["suspect_leakage"] is True
    assert "[SUSPECT LEAKAGE]" in scoring["leakage_flag"]


def test_score_contains_required_fields():
    output = "## Primary Prediction\nBitcoin reaches target with 65% probability."
    scoring = score_prediction(SAMPLE_EVENT, output)
    required = ["primary_confidence", "alignment_score", "suspect_leakage",
                "leakage_flag", "score_method"]
    for field in required:
        assert field in scoring, f"Missing field: {field}"


def test_score_alignment_score_is_float():
    output = "Bitcoin will likely reach new highs given current momentum."
    scoring = score_prediction(SAMPLE_EVENT, output)
    assert isinstance(scoring["alignment_score"], float)
    assert 0.0 <= scoring["alignment_score"] <= 1.0


# ---------------------------------------------------------------------------
# select_unrun_events
# ---------------------------------------------------------------------------

def test_select_skips_completed_events():
    events = [
        {"event_id": "ev-1"},
        {"event_id": "ev-2"},
        {"event_id": "ev-3"},
    ]
    state = {"completed": {"ev-1": {"date": "2026-04-01"}}}
    selected = select_unrun_events(events, state, limit=5)
    ids = [e["event_id"] for e in selected]
    assert "ev-1" not in ids
    assert "ev-2" in ids
    assert "ev-3" in ids


def test_select_respects_limit():
    events = [{"event_id": f"ev-{i}"} for i in range(10)]
    selected = select_unrun_events(events, {}, limit=3)
    assert len(selected) == 3


def test_select_returns_empty_when_all_done():
    events = [{"event_id": "ev-1"}, {"event_id": "ev-2"}]
    state = {"completed": {"ev-1": {}, "ev-2": {}}}
    selected = select_unrun_events(events, state, limit=5)
    assert selected == []


# ---------------------------------------------------------------------------
# load_events (integration -- requires data/backtest_events.yaml)
# ---------------------------------------------------------------------------

def test_load_events_returns_list():
    events = load_events()
    assert isinstance(events, list)


def test_load_events_minimum_count():
    events = load_events()
    assert len(events) >= 25, f"Expected >= 25 events, got {len(events)}"


def test_load_events_required_fields():
    events = load_events()
    required_fields = [
        "event_id", "description", "domain",
        "knowledge_cutoff_date", "known_outcome",
        "difficulty", "at_time_context",
    ]
    for event in events:
        for field in required_fields:
            assert field in event, f"Event {event.get('event_id', '?')} missing field: {field}"


def test_load_events_valid_domains():
    valid_domains = {"geopolitics", "market", "technology", "planning", "other"}
    events = load_events()
    for event in events:
        assert event["domain"] in valid_domains, (
            f"Event {event['event_id']} has invalid domain: {event['domain']}"
        )


def test_load_events_valid_difficulty():
    valid_difficulties = {"low", "medium", "high"}
    events = load_events()
    for event in events:
        assert event["difficulty"] in valid_difficulties, (
            f"Event {event['event_id']} has invalid difficulty: {event['difficulty']}"
        )


def test_load_events_unique_ids():
    events = load_events()
    ids = [e["event_id"] for e in events]
    assert len(ids) == len(set(ids)), "Duplicate event_ids found in backtest_events.yaml"


# ---------------------------------------------------------------------------
# Frontmatter output validation
# ---------------------------------------------------------------------------

def test_prediction_file_required_frontmatter(tmp_path):
    """Ensure written prediction file contains required frontmatter fields."""
    scoring = {
        "primary_confidence": 0.65,
        "alignment_score": 0.6,
        "suspect_leakage": False,
        "leakage_flag": "",
        "score_method": "keyword-alignment-v1",
    }

    # Temporarily redirect PREDICTIONS_DIR
    import tools.scripts.prediction_backtest_producer as module
    original = module.PREDICTIONS_DIR
    module.PREDICTIONS_DIR = tmp_path

    try:
        output_path = write_prediction_file(SAMPLE_EVENT, "Test output 65%", scoring)
        content = output_path.read_text(encoding="utf-8")
        assert "backtested: true" in content
        assert "leakage_risk: HIGH" in content
        assert "weight: 0.5" in content
        assert "status: pending_review" in content
    finally:
        module.PREDICTIONS_DIR = original


def test_suspect_leakage_flag_in_file(tmp_path):
    """Files with high-confidence predictions carry SUSPECT LEAKAGE marker."""
    scoring = {
        "primary_confidence": 0.92,
        "alignment_score": 0.8,
        "suspect_leakage": True,
        "leakage_flag": "[SUSPECT LEAKAGE]",
        "score_method": "keyword-alignment-v1",
    }

    import tools.scripts.prediction_backtest_producer as module
    original = module.PREDICTIONS_DIR
    module.PREDICTIONS_DIR = tmp_path

    try:
        output_path = write_prediction_file(SAMPLE_EVENT, "Test output 92%", scoring)
        content = output_path.read_text(encoding="utf-8")
        assert "SUSPECT LEAKAGE" in content
        assert "suspect_leakage: true" in content
    finally:
        module.PREDICTIONS_DIR = original
