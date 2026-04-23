"""Tests for tools/scripts/verify_goal_drift.py."""
import sys
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import tools.scripts.verify_goal_drift as vgd


def _today():
    return datetime.now(timezone.utc).strftime("%Y-%m-%d")


def test_log_exists_nonempty(tmp_path):
    f = tmp_path / f"goal_drift_{_today()}.log"
    f.write_text("G1: last_capture=2026-01-01 age_days=5\n", encoding="utf-8")
    with patch.object(vgd, "LOG_DIR", tmp_path):
        assert vgd.main() == 0


def test_log_missing(tmp_path):
    with patch.object(vgd, "LOG_DIR", tmp_path):
        assert vgd.main() == 1


def test_log_empty_file(tmp_path):
    f = tmp_path / f"goal_drift_{_today()}.log"
    f.write_text("", encoding="utf-8")
    with patch.object(vgd, "LOG_DIR", tmp_path):
        assert vgd.main() == 1


def test_wrong_date_log_not_counted(tmp_path):
    f = tmp_path / "goal_drift_2020-01-01.log"
    f.write_text("G1: last_capture=2019-01-01\n", encoding="utf-8")
    with patch.object(vgd, "LOG_DIR", tmp_path):
        assert vgd.main() == 1
