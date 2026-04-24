"""Tests for vitals_collector.py pure helper functions."""

import json
import tempfile
from datetime import datetime, timezone
from pathlib import Path

from tools.scripts.vitals_collector import (
    collect_contradictions_structured,
    collect_external_monitoring_structured,
    collect_proposals_structured,
    compute_trend_averages,
    _summarize_overnight_log,
    _task_scheduler_result_label,
    load_ai_pricing,
    check_ai_pricing_staleness,
    apply_gemini_pricing,
)


# ---------------------------------------------------------------------------
# compute_trend_averages
# ---------------------------------------------------------------------------

def test_task_scheduler_result_label_zero():
    assert _task_scheduler_result_label(0) == "SUCCESS"


def test_task_scheduler_result_label_has_not_run():
    assert _task_scheduler_result_label(0x00041303) == "SCHED_S_TASK_HAS_NOT_RUN"


def test_summarize_overnight_log_success_exit_zero():
    body = "line\n[2026-04-22] Overnight complete (exit code: 0)\n"
    status, code, hint = _summarize_overnight_log(body)
    assert status == "ran"
    assert code == 0
    assert hint == ""


def test_summarize_overnight_log_failed_exit_one():
    body = (
        "ERROR: memory link hide failed\n"
        "self-diagnose: failure detected (exit code: 1)\n"
        "[2026-04-22] Overnight self-improvement complete (exit code: 1)\n"
    )
    status, code, hint = _summarize_overnight_log(body)
    assert status == "failed"
    assert code == 1
    assert "memory link" in hint.lower() or "junction" in hint.lower()


def test_compute_trend_averages_empty():
    assert compute_trend_averages([]) == {}


def test_compute_trend_averages_single_entry():
    trend = [{"metrics": {"signal_count": {"value": 10}}}]
    result = compute_trend_averages(trend)
    assert "signal_count" in result
    assert result["signal_count"]["avg"] == 10.0
    assert result["signal_count"]["min"] == 10
    assert result["signal_count"]["max"] == 10
    assert result["signal_count"]["samples"] == 1


def test_compute_trend_averages_multiple_entries():
    trend = [
        {"metrics": {"isc_ratio": {"value": 0.5}}},
        {"metrics": {"isc_ratio": {"value": 0.7}}},
        {"metrics": {"isc_ratio": {"value": 0.9}}},
    ]
    result = compute_trend_averages(trend)
    assert result["isc_ratio"]["avg"] == pytest_approx_or_round(0.7)
    assert result["isc_ratio"]["min"] == 0.5
    assert result["isc_ratio"]["max"] == 0.9
    assert result["isc_ratio"]["samples"] == 3


def pytest_approx_or_round(value, ndigits=4):
    return round(value, ndigits)


def test_compute_trend_averages_skips_none_values():
    trend = [
        {"metrics": {"signal_count": {"value": None}}},
        {"metrics": {"signal_count": {"value": 5}}},
    ]
    result = compute_trend_averages(trend)
    assert result["signal_count"]["samples"] == 1
    assert result["signal_count"]["avg"] == 5.0


def test_compute_trend_averages_missing_metric_not_included():
    trend = [{"metrics": {}}]
    result = compute_trend_averages(trend)
    assert "signal_count" not in result


# ---------------------------------------------------------------------------
# collect_external_monitoring_structured
# ---------------------------------------------------------------------------

def test_external_monitoring_none_input():
    assert collect_external_monitoring_structured(None) is None


def test_external_monitoring_no_key():
    assert collect_external_monitoring_structured({}) is None


def test_external_monitoring_empty_string():
    assert collect_external_monitoring_structured({"external_monitoring": ""}) is None


def test_external_monitoring_parses_sections():
    md = "### Crypto Markets\n- BTC holding support\n- Volume elevated\n"
    result = collect_external_monitoring_structured({"external_monitoring": md})
    assert result is not None
    assert len(result) == 1
    assert result[0]["category"] == "Crypto Markets"
    assert "BTC holding support" in result[0]["items"]


def test_external_monitoring_skips_meta_headings():
    md = "## Summary\n- Skip this\n### Crypto Markets\n- Real item\n"
    result = collect_external_monitoring_structured({"external_monitoring": md})
    # Summary heading should be skipped
    assert result is not None
    assert all(s["category"] != "Summary" for s in result)


# ---------------------------------------------------------------------------
# collect_contradictions_structured
# ---------------------------------------------------------------------------

def test_contradictions_none_input():
    assert collect_contradictions_structured(None) is None


def test_contradictions_empty():
    assert collect_contradictions_structured({"autoresearch_contradictions": ""}) is None


def test_contradictions_parses_entry():
    md = (
        "- TELOS claim: I build lean systems\n"
        "- Signal evidence: 3 new dependencies added this week\n"
        "- Severity: HIGH\n"
    )
    result = collect_contradictions_structured({"autoresearch_contradictions": md})
    assert result is not None
    assert len(result) == 1
    assert "lean systems" in result[0]["claim"]
    assert result[0]["severity"] == "HIGH"


def test_contradictions_defaults_severity():
    md = "- TELOS claim: Something\n- Signal evidence: Evidence here\n"
    result = collect_contradictions_structured({"autoresearch_contradictions": md})
    assert result[0]["severity"] == "MEDIUM"


# ---------------------------------------------------------------------------
# collect_proposals_structured
# ---------------------------------------------------------------------------

def test_proposals_none_input():
    assert collect_proposals_structured(None) is None


def test_proposals_empty():
    assert collect_proposals_structured({"autoresearch_proposals": ""}) is None


def test_proposals_parses_entry():
    md = (
        "- File: memory/work/TELOS.md\n"
        "- Change: Update mission statement\n"
        "- Evidence: 3 signals point to this\n"
    )
    result = collect_proposals_structured({"autoresearch_proposals": md})
    assert result is not None
    assert len(result) == 1
    assert "TELOS.md" in result[0]["file"]
    assert "mission" in result[0]["change"]


def test_proposals_defaults_missing_fields():
    md = "- File: some/file.md\n"
    result = collect_proposals_structured({"autoresearch_proposals": md})
    assert result[0]["change"] == ""
    assert result[0]["evidence"] == ""


# ---------------------------------------------------------------------------
# load_ai_pricing
# ---------------------------------------------------------------------------

def test_load_ai_pricing_valid_file():
    data = {"gemini": {"flash": {"output_per_1m_usd": 0.6}}, "verified_at": "2026-01-01T00:00:00"}
    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False, encoding="utf-8") as f:
        json.dump(data, f)
        fpath = Path(f.name)
    result = load_ai_pricing(fpath)
    assert result is not None
    assert "gemini" in result


def test_load_ai_pricing_missing_file():
    result = load_ai_pricing(Path("nonexistent_pricing_xyz.json"))
    assert result is None


def test_load_ai_pricing_invalid_json():
    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False, encoding="utf-8") as f:
        f.write("{not valid json")
        fpath = Path(f.name)
    result = load_ai_pricing(fpath)
    assert result is None


# ---------------------------------------------------------------------------
# check_ai_pricing_staleness
# ---------------------------------------------------------------------------

def test_check_staleness_none_pricing():
    assert check_ai_pricing_staleness(None) is None


def test_check_staleness_missing_verified_at():
    result = check_ai_pricing_staleness({"gemini": {}})
    assert result == "ai_pricing_unparseable"


def test_check_staleness_malformed_date():
    result = check_ai_pricing_staleness({"verified_at": "not-a-date"})
    assert result == "ai_pricing_unparseable"


def test_check_staleness_fresh():
    now = datetime(2026, 4, 24, tzinfo=timezone.utc)
    pricing = {"verified_at": "2026-04-22T00:00:00+00:00"}
    assert check_ai_pricing_staleness(pricing, now=now) is None


def test_check_staleness_stale():
    now = datetime(2026, 4, 24, tzinfo=timezone.utc)
    pricing = {"verified_at": "2026-03-01T00:00:00+00:00"}
    result = check_ai_pricing_staleness(pricing, now=now, stale_days=7)
    assert result == "ai_pricing_stale"


def test_check_staleness_naive_dt_treated_as_utc():
    now = datetime(2026, 4, 24, tzinfo=timezone.utc)
    pricing = {"verified_at": "2026-04-23T00:00:00"}  # no tz info
    assert check_ai_pricing_staleness(pricing, now=now, stale_days=7) is None


# ---------------------------------------------------------------------------
# apply_gemini_pricing
# ---------------------------------------------------------------------------

def _pricing(output_rate=0.6, input_rate=0.075):
    return {"gemini": {"flash": {"output_per_1m_usd": output_rate, "input_per_1m_usd": input_rate}}}


def test_apply_gemini_pricing_computes_cost():
    gemini = {"month": {"tokens": 1_000_000}, "week": {"tokens": 500_000}}
    apply_gemini_pricing(gemini, _pricing(output_rate=1.0))
    assert gemini["cost_usd_month"] == 1.0
    assert gemini["cost_usd_week"] == 0.5


def test_apply_gemini_pricing_none_gemini():
    apply_gemini_pricing(None, _pricing())  # should not raise


def test_apply_gemini_pricing_none_pricing():
    gemini = {"month": {"tokens": 100}}
    apply_gemini_pricing(gemini, None)
    assert "cost_usd_month" not in gemini


def test_apply_gemini_pricing_zero_rate_skipped():
    gemini = {"month": {"tokens": 1_000_000}}
    apply_gemini_pricing(gemini, _pricing(output_rate=0.0))
    assert "cost_usd_month" not in gemini


def test_apply_gemini_pricing_invalid_rate_skipped():
    gemini = {"month": {"tokens": 1_000_000}}
    apply_gemini_pricing(gemini, {"gemini": {"flash": {"output_per_1m_usd": "bad"}}})
    assert "cost_usd_month" not in gemini


def test_apply_gemini_pricing_adds_assumption_field():
    gemini = {"month": {"tokens": 0}, "week": {"tokens": 0}}
    apply_gemini_pricing(gemini, _pricing())
    assert gemini["pricing_assumption"] == "output_rate_upper_bound"
