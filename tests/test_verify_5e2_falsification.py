"""Tests for verify_5e2_falsification.py -- Phase 5E-2 invariant checks."""
from __future__ import annotations

import importlib.util
from datetime import date
from pathlib import Path

SCRIPT = Path(__file__).parents[1] / "tools" / "scripts" / "verify_5e2_falsification.py"


def _load():
    spec = importlib.util.spec_from_file_location("verify_5e2", SCRIPT)
    mod = importlib.util.module_from_spec(spec)  # type: ignore[arg-type]
    spec.loader.exec_module(mod)  # type: ignore[union-attr]
    return mod


TODAY = date(2026, 4, 14)


def _task(**kwargs):
    base = {"id": "t1", "status": "pending_review", "created": "2026-04-07", "generation": 1}
    base.update(kwargs)
    return base


class TestTaskAgeDays:
    def test_returns_correct_days(self):
        mod = _load()
        task = _task(created="2026-04-07")
        assert mod._task_age_days(task, TODAY) == 7

    def test_returns_none_for_missing_created(self):
        mod = _load()
        assert mod._task_age_days({}, TODAY) is None

    def test_returns_none_for_bad_date(self):
        mod = _load()
        assert mod._task_age_days({"created": "not-a-date"}, TODAY) is None

    def test_returns_zero_for_today(self):
        mod = _load()
        task = _task(created="2026-04-14")
        assert mod._task_age_days(task, TODAY) == 0


class TestI2NoStalePendingReview:
    def test_pass_when_no_old_tasks(self):
        mod = _load()
        backlog = [_task(id="t1", created="2026-04-10", status="pending_review")]  # 4 days
        status, _ = mod.check_i2_no_stale_pending_review(backlog, TODAY)
        assert status == mod.PASS

    def test_fail_when_task_14d_plus(self):
        mod = _load()
        backlog = [_task(id="t1", created="2026-03-31", status="pending_review")]  # 14 days
        status, detail = mod.check_i2_no_stale_pending_review(backlog, TODAY)
        assert status == mod.FAIL
        assert "t1" in detail

    def test_ignores_non_pending_review(self):
        mod = _load()
        backlog = [_task(id="t1", created="2026-01-01", status="done")]
        status, _ = mod.check_i2_no_stale_pending_review(backlog, TODAY)
        assert status == mod.PASS

    def test_pass_when_13_days_old(self):
        mod = _load()
        backlog = [_task(id="t1", created="2026-04-01", status="pending_review")]  # 13 days
        status, _ = mod.check_i2_no_stale_pending_review(backlog, TODAY)
        assert status == mod.PASS


class TestI4NoGenerationOverflow:
    def test_pass_when_all_gen_le_2(self):
        mod = _load()
        backlog = [_task(generation=1), _task(id="t2", generation=2)]
        status, _ = mod.check_i4_no_generation_overflow(backlog, [])
        assert status == mod.PASS

    def test_fail_when_gen_3(self):
        mod = _load()
        backlog = [_task(id="t1", generation=3)]
        status, detail = mod.check_i4_no_generation_overflow(backlog, [])
        assert status == mod.FAIL
        assert "t1" in detail

    def test_pass_when_no_generation_field(self):
        mod = _load()
        task = {"id": "t1", "status": "done"}
        status, _ = mod.check_i4_no_generation_overflow([task], [])
        assert status == mod.PASS

    def test_checks_archive_too(self):
        mod = _load()
        archive = [_task(id="archived", generation=3)]
        status, _ = mod.check_i4_no_generation_overflow([], archive)
        assert status == mod.FAIL


class TestI5BranchLifecycleRouting:
    def test_skip_when_no_branch_lifecycle_tasks(self):
        mod = _load()
        status, _ = mod.check_i5_branch_lifecycle_routing([], [])
        assert status == mod.SKIP

    def test_pass_when_all_in_manual_review(self):
        mod = _load()
        t = {"id": "t1", "failure_type": "branch_lifecycle", "status": "manual_review"}
        status, _ = mod.check_i5_branch_lifecycle_routing([t], [])
        assert status == mod.PASS

    def test_pass_when_in_failed_status(self):
        mod = _load()
        t = {"id": "t1", "failure_type": "branch_lifecycle", "status": "failed"}
        status, _ = mod.check_i5_branch_lifecycle_routing([t], [])
        assert status == mod.PASS

    def test_fail_when_still_pending_review(self):
        mod = _load()
        t = {"id": "t1", "failure_type": "branch_lifecycle", "status": "pending_review"}
        status, detail = mod.check_i5_branch_lifecycle_routing([t], [])
        assert status == mod.FAIL
        assert "t1" in detail


class TestI3ExpireArchiveIntegrity:
    def test_skip_when_no_ttl_failed_tasks(self):
        mod = _load()
        status, _ = mod.check_i3_expire_archive_integrity([], [], TODAY)
        assert status == mod.SKIP

    def test_fail_when_ttl_task_missing_archive_record(self, tmp_path, monkeypatch):
        mod = _load()
        # No expired archive dir
        monkeypatch.setattr(mod, "PENDING_REVIEW_EXPIRED_DIR", tmp_path / "empty_dir")
        t = {"id": "t1", "failure_type": "pending_review_ttl", "status": "failed"}
        status, detail = mod.check_i3_expire_archive_integrity([t], [], TODAY)
        assert status == mod.FAIL
        assert "t1" in detail

    def test_pass_when_archive_record_exists(self, tmp_path, monkeypatch):
        mod = _load()
        expired_dir = tmp_path / "expired"
        expired_dir.mkdir()
        import json
        (expired_dir / "t1.json").write_text(json.dumps({"task_id": "t1"}))
        monkeypatch.setattr(mod, "PENDING_REVIEW_EXPIRED_DIR", expired_dir)
        t = {"id": "t1", "failure_type": "pending_review_ttl", "status": "failed"}
        status, _ = mod.check_i3_expire_archive_integrity([t], [], TODAY)
        assert status == mod.PASS
