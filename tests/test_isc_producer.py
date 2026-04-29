"""Tests for isc_producer.py pure helper functions."""
from __future__ import annotations

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from tools.scripts.isc_producer import classify_near_miss, criterion_hash, build_report


class TestClassifyNearMiss:
    def _criterion(self, verdict="FAIL", evidence="", verify=""):
        return {"verdict": verdict, "evidence": evidence, "verify_method": verify}

    def test_non_fail_returns_false(self):
        assert classify_near_miss(self._criterion(verdict="PASS")) is False

    def test_manual_returns_false(self):
        assert classify_near_miss(self._criterion(verdict="MANUAL")) is False

    def test_grep_negation_returns_false(self):
        assert classify_near_miss(self._criterion(verdict="FAIL", verify="grep!: pattern")) is False

    def test_file_found_evidence_is_near_miss(self):
        assert classify_near_miss(self._criterion(verdict="FAIL", evidence="file found at path")) is True

    def test_directory_found_evidence_is_near_miss(self):
        assert classify_near_miss(self._criterion(verdict="FAIL", evidence="directory found")) is True

    def test_exists_evidence_is_near_miss(self):
        assert classify_near_miss(self._criterion(verdict="FAIL", evidence="target exists")) is True

    def test_one_match_evidence_is_near_miss(self):
        assert classify_near_miss(self._criterion(verdict="FAIL", evidence="1 match found")) is True

    def test_empty_evidence_not_near_miss(self):
        assert classify_near_miss(self._criterion(verdict="FAIL", evidence="")) is False

    def test_unrelated_evidence_not_near_miss(self):
        assert classify_near_miss(self._criterion(verdict="FAIL", evidence="command failed with error")) is False


class TestCriterionHash:
    def test_returns_12_char_hex(self):
        h = criterion_hash("some criterion text")
        assert len(h) == 12
        assert all(c in "0123456789abcdef" for c in h)

    def test_same_text_same_hash(self):
        assert criterion_hash("hello") == criterion_hash("hello")

    def test_different_text_different_hash(self):
        assert criterion_hash("abc") != criterion_hash("xyz")

    def test_empty_string_produces_hash(self):
        h = criterion_hash("")
        assert len(h) == 12


class TestBuildReport:
    def _prd_result(self, prd_path, criteria):
        return {
            "prd_path": prd_path,
            "executor_output": {"criteria": criteria},
        }

    def _criterion(self, verdict, text="criterion text", verify="cmd"):
        return {"verdict": verdict, "criterion": text, "evidence": "output", "verify_method": verify}

    def test_empty_results(self):
        report = build_report([], 1.5, 0, run_date="2026-04-01T00:00:00Z")
        assert report["summary"] == {"pass": 0, "fail": 0, "manual": 0, "error": 0}
        assert report["prds_scanned"] == 0
        assert report["near_miss_tasks_created"] == 0

    def test_duration_rounded(self):
        report = build_report([], 1.23456, 0, run_date="2026-04-01T00:00:00Z")
        assert report["run_duration_s"] == 1.23

    def test_timeout_flag(self):
        report = build_report([], 5.0, 0, timeout_hit=True, run_date="2026-04-01T00:00:00Z")
        assert report["timeout_hit"] is True

    def test_pass_counts_aggregated(self):
        result = self._prd_result("prd.md", [
            self._criterion("pass"),
            self._criterion("pass"),
            self._criterion("FAIL"),
        ])
        report = build_report([result], 1.0, 0, run_date="2026-04-01T00:00:00Z")
        assert report["summary"]["pass"] == 2
        assert report["summary"]["fail"] == 1

    def test_none_executor_output_marked_error(self):
        result = {"prd_path": "bad.md", "executor_output": None}
        report = build_report([result], 1.0, 0, run_date="2026-04-01T00:00:00Z")
        assert report["by_prd"][0]["status"] == "ERROR"

    def test_run_date_propagated(self):
        report = build_report([], 0.5, 0, run_date="2026-04-28T10:00:00Z")
        assert report["run_date"] == "2026-04-28T10:00:00Z"

    def test_prds_scanned_count(self):
        results = [
            self._prd_result("a.md", []),
            self._prd_result("b.md", []),
        ]
        report = build_report(results, 1.0, 0, run_date="2026-04-01T00:00:00Z")
        assert report["prds_scanned"] == 2
