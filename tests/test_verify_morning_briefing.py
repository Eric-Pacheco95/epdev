"""Tests for tools/scripts/verify_morning_briefing.py."""
import sys
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import tools.scripts.verify_morning_briefing as vmb


def _today():
    return datetime.now(timezone.utc).strftime("%Y-%m-%d")


def test_log_exists_nonempty(tmp_path):
    f = tmp_path / f"morning_briefing_{_today()}.log"
    f.write_text("briefing content\n", encoding="utf-8")
    with patch.object(vmb, "LOG_DIR", tmp_path):
        assert vmb.main() == 0


def test_log_missing(tmp_path):
    with patch.object(vmb, "LOG_DIR", tmp_path):
        assert vmb.main() == 1


def test_log_empty_file(tmp_path):
    f = tmp_path / f"morning_briefing_{_today()}.log"
    f.write_text("", encoding="utf-8")
    with patch.object(vmb, "LOG_DIR", tmp_path):
        assert vmb.main() == 1


def test_wrong_date_not_counted(tmp_path):
    f = tmp_path / "morning_briefing_2020-01-01.log"
    f.write_text("old content\n", encoding="utf-8")
    with patch.object(vmb, "LOG_DIR", tmp_path):
        assert vmb.main() == 1
