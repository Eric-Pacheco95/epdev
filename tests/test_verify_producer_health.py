"""Tests for tools/scripts/verify_producer_health.py."""
import sys
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import tools.scripts.verify_producer_health as vph


def test_all_healthy(monkeypatch):
    monkeypatch.setattr(sys, "argv", ["prog"])
    with patch("tools.scripts.verify_producer_health.query_producer_health", return_value=[]):
        assert vph.main() == 0


def test_one_unhealthy(monkeypatch):
    monkeypatch.setattr(sys, "argv", ["prog"])
    issues = [{"producer": "heartbeat", "issue": "stale", "hours_ago": 30.0, "last_status": "ok"}]
    with patch("tools.scripts.verify_producer_health.query_producer_health", return_value=issues):
        assert vph.main() == 1


def test_custom_max_age_passed_through(monkeypatch):
    monkeypatch.setattr(sys, "argv", ["prog", "--max-age-hours", "48"])
    captured_kwargs = {}

    def fake_query(max_age_hours=26.0):
        captured_kwargs["max_age_hours"] = max_age_hours
        return []

    with patch("tools.scripts.verify_producer_health.query_producer_health", side_effect=fake_query):
        vph.main()

    assert captured_kwargs["max_age_hours"] == 48.0


def test_multiple_unhealthy_reported(monkeypatch):
    monkeypatch.setattr(sys, "argv", ["prog"])
    issues = [
        {"producer": "p1", "issue": "stale", "hours_ago": 10.0, "last_status": "fail"},
        {"producer": "p2", "issue": "missing", "hours_ago": 5.0, "last_status": "ok"},
    ]
    with patch("tools.scripts.verify_producer_health.query_producer_health", return_value=issues):
        assert vph.main() == 1
