"""Tests for prediction_backtest_producer.py -- pure helper functions."""
from __future__ import annotations

import importlib.util
from pathlib import Path

SCRIPT = Path(__file__).parents[1] / "tools" / "scripts" / "prediction_backtest_producer.py"


def _load():
    spec = importlib.util.spec_from_file_location("prediction_backtest_producer", SCRIPT)
    mod = importlib.util.module_from_spec(spec)  # type: ignore[arg-type]
    spec.loader.exec_module(mod)  # type: ignore[union-attr]
    return mod


class TestSelectUnrunEvents:
    def _events(self):
        return [
            {"event_id": "e1", "status": "approved"},
            {"event_id": "e2", "status": "proposed"},
            {"event_id": "e3", "status": "rejected"},
            {"event_id": "e4"},  # legacy, no status
            {"event_id": "e5", "status": "approved"},
        ]

    def test_excludes_proposed(self):
        mod = _load()
        result = mod.select_unrun_events(self._events(), {}, limit=10)
        ids = [e["event_id"] for e in result]
        assert "e2" not in ids

    def test_excludes_rejected(self):
        mod = _load()
        result = mod.select_unrun_events(self._events(), {}, limit=10)
        ids = [e["event_id"] for e in result]
        assert "e3" not in ids

    def test_includes_approved_and_legacy(self):
        mod = _load()
        result = mod.select_unrun_events(self._events(), {}, limit=10)
        ids = [e["event_id"] for e in result]
        assert "e1" in ids
        assert "e4" in ids
        assert "e5" in ids

    def test_excludes_completed_events(self):
        mod = _load()
        state = {"completed": {"e1": {}}}
        result = mod.select_unrun_events(self._events(), state, limit=10)
        ids = [e["event_id"] for e in result]
        assert "e1" not in ids

    def test_respects_limit(self):
        mod = _load()
        result = mod.select_unrun_events(self._events(), {}, limit=2)
        assert len(result) <= 2


class TestExtractPrimaryConfidence:
    def test_extracts_percentage_from_primary_section(self):
        mod = _load()
        output = """## Outcomes
- Outcome A: 30%
- Outcome B: 70%

## Primary Prediction
Outcome B is most likely at 70%.

## Signposts
..."""
        conf = mod.extract_primary_confidence(output)
        assert conf is not None
        assert 0.0 < conf <= 1.0

    def test_returns_none_when_no_percentage(self):
        mod = _load()
        output = "The model cannot determine any probability."
        assert mod.extract_primary_confidence(output) is None

    def test_ignores_over_100_pct(self):
        mod = _load()
        output = "## Primary Prediction\n200% chance -- clearly invalid"
        result = mod.extract_primary_confidence(output)
        assert result is None

    def test_returns_float_between_0_and_1(self):
        mod = _load()
        output = "## Primary Prediction\n65% chance this happens"
        result = mod.extract_primary_confidence(output)
        assert result is not None
        assert 0.0 < result <= 1.0
        assert result == 0.65


class TestScorePrediction:
    def _event(self, outcome="market declined due to recession fears"):
        return {"event_id": "e1", "known_outcome": outcome}

    def test_returns_required_fields(self):
        mod = _load()
        scoring = mod.score_prediction(self._event(), "Some prediction output")
        assert "primary_confidence" in scoring
        assert "alignment_score" in scoring
        assert "suspect_leakage" in scoring
        assert "leakage_flag" in scoring
        assert "score_method" in scoring

    def test_suspect_leakage_false_for_low_confidence(self):
        mod = _load()
        output = "## Primary Prediction\n50% chance"
        scoring = mod.score_prediction(self._event(), output)
        assert scoring["suspect_leakage"] is False
        assert scoring["leakage_flag"] == ""

    def test_suspect_leakage_true_for_high_confidence(self):
        mod = _load()
        output = "## Primary Prediction\n90% chance"
        scoring = mod.score_prediction(self._event(), output)
        assert scoring["suspect_leakage"] is True
        assert "[SUSPECT LEAKAGE]" in scoring["leakage_flag"]

    def test_alignment_score_between_0_and_1(self):
        mod = _load()
        output = "The market declined due to recession concerns and fears of slowdown"
        scoring = mod.score_prediction(self._event(), output)
        assert 0.0 <= scoring["alignment_score"] <= 1.0

    def test_alignment_score_higher_with_matching_keywords(self):
        mod = _load()
        event = self._event("bitcoin halving")
        high_match = "bitcoin halving event occurred as expected"
        low_match = "completely unrelated topic"
        high_score = mod.score_prediction(event, high_match)["alignment_score"]
        low_score = mod.score_prediction(event, low_match)["alignment_score"]
        assert high_score > low_score


class TestBuildPrompt:
    def test_prompt_contains_cutoff_date(self):
        mod = _load()
        event = {
            "event_id": "e1",
            "knowledge_cutoff_date": "2022-01-01",
            "at_time_context": "Some context.",
            "description": "Will X happen?",
        }
        prompt = mod.build_prompt(event)
        assert "2022-01-01" in prompt

    def test_prompt_contains_description(self):
        mod = _load()
        event = {
            "event_id": "e1",
            "knowledge_cutoff_date": "2022-01-01",
            "at_time_context": "Context.",
            "description": "Will the Fed raise rates?",
        }
        prompt = mod.build_prompt(event)
        assert "Will the Fed raise rates?" in prompt


class TestAppendAnalysisToFile:
    def test_appends_analysis(self, tmp_path):
        mod = _load()
        p = tmp_path / "pred.md"
        p.write_text("---\ntitle: T\n---\n\nBody.\n", encoding="utf-8")
        mod.append_analysis_to_file(p, "## Prediction Analysis\nResult.")
        text = p.read_text()
        assert "Prediction Analysis" in text
        assert "Result." in text

    def test_skips_if_analysis_exists(self, tmp_path):
        mod = _load()
        p = tmp_path / "pred.md"
        original = "---\ntitle: T\n---\n\n## Prediction Analysis\nOld.\n"
        p.write_text(original, encoding="utf-8")
        mod.append_analysis_to_file(p, "## Prediction Analysis\nNew.")
        text = p.read_text()
        assert text.count("Prediction Analysis") == 1
        assert "Old." in text
