"""Tests for vitals_collector.py pure helper functions."""

from tools.scripts.vitals_collector import (
    collect_contradictions_structured,
    collect_external_monitoring_structured,
    collect_proposals_structured,
    compute_trend_averages,
    _summarize_overnight_log,
    _task_scheduler_result_label,
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
        "ERROR: junction hide failed\n"
        "self-diagnose: failure detected (exit code: 1)\n"
        "[2026-04-22] Overnight self-improvement complete (exit code: 1)\n"
    )
    status, code, hint = _summarize_overnight_log(body)
    assert status == "failed"
    assert code == 1
    assert "junction" in hint.lower()


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
