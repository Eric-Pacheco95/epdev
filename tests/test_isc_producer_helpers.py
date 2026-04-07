"""Tests for isc_producer.py pure helper functions."""

import hashlib

from tools.scripts.isc_producer import classify_near_miss, criterion_hash, build_report


# ---------------------------------------------------------------------------
# classify_near_miss
# ---------------------------------------------------------------------------

def test_classify_near_miss_not_fail():
    assert classify_near_miss({"verdict": "PASS", "evidence": "file found"}) is False


def test_classify_near_miss_anti_criterion_skipped():
    c = {"verdict": "FAIL", "evidence": "file found", "verify_method": "Grep!:some pattern"}
    assert classify_near_miss(c) is False


def test_classify_near_miss_file_found_signal():
    c = {"verdict": "FAIL", "evidence": "file found at path", "verify_method": "Read"}
    assert classify_near_miss(c) is True


def test_classify_near_miss_exists_signal():
    c = {"verdict": "FAIL", "evidence": "directory exists but empty", "verify_method": "Read"}
    assert classify_near_miss(c) is True


def test_classify_near_miss_no_signal():
    c = {"verdict": "FAIL", "evidence": "nothing found at all", "verify_method": "Read"}
    assert classify_near_miss(c) is False


def test_classify_near_miss_missing_evidence():
    c = {"verdict": "FAIL"}
    assert classify_near_miss(c) is False


# ---------------------------------------------------------------------------
# criterion_hash
# ---------------------------------------------------------------------------

def test_criterion_hash_length():
    h = criterion_hash("some criterion text")
    assert len(h) == 12


def test_criterion_hash_deterministic():
    assert criterion_hash("abc") == criterion_hash("abc")


def test_criterion_hash_different_inputs():
    assert criterion_hash("criterion A") != criterion_hash("criterion B")


def test_criterion_hash_matches_sha256_prefix():
    text = "test criterion"
    expected = hashlib.sha256(text.encode()).hexdigest()[:12]
    assert criterion_hash(text) == expected


# ---------------------------------------------------------------------------
# build_report
# ---------------------------------------------------------------------------

def test_build_report_empty():
    report = build_report([], 1.5, 0, run_date="2026-01-01T00:00:00Z")
    assert report["summary"] == {"pass": 0, "fail": 0, "manual": 0, "error": 0}
    assert report["prds_scanned"] == 0
    assert report["near_miss_tasks_created"] == 0
    assert report["run_date"] == "2026-01-01T00:00:00Z"


def test_build_report_counts_pass_fail():
    prd_results = [{
        "prd_path": "memory/work/test.md",
        "executor_output": {
            "criteria": [
                {"verdict": "PASS", "criterion": "C1", "evidence": "ok", "verify_method": "Read"},
                {"verdict": "FAIL", "criterion": "C2", "evidence": "missing", "verify_method": "Grep"},
            ]
        }
    }]
    report = build_report(prd_results, 2.0, 0, run_date="2026-01-01T00:00:00Z")
    assert report["summary"]["pass"] == 1
    assert report["summary"]["fail"] == 1
    assert len(report["ready_to_mark"]) == 1


def test_build_report_none_executor_output():
    prd_results = [{"prd_path": "memory/work/broken.md", "executor_output": None}]
    report = build_report(prd_results, 1.0, 0, run_date="2026-01-01T00:00:00Z")
    assert report["by_prd"][0]["status"] == "ERROR"
    assert report["summary"] == {"pass": 0, "fail": 0, "manual": 0, "error": 0}
