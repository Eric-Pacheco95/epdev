"""Tests for tools/scripts/verify_vitals_schema.py main()."""
from __future__ import annotations

import json
import sys
from pathlib import Path
from unittest.mock import patch, MagicMock

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

import tools.scripts.verify_vitals_schema as vvs


def _make_run_result(stdout: str = "", returncode: int = 0, stderr: str = "") -> MagicMock:
    result = MagicMock()
    result.stdout = stdout
    result.returncode = returncode
    result.stderr = stderr
    return result


class TestBaselineKeys:
    def test_baseline_10_exists(self):
        assert "1.0.0" in vvs.BASELINE_KEYS

    def test_baseline_10_has_schema_version(self):
        assert "_schema_version" in vvs.BASELINE_KEYS["1.0.0"]

    def test_baseline_10_has_heartbeat(self):
        assert "heartbeat" in vvs.BASELINE_KEYS["1.0.0"]

    def test_baseline_10_has_errors(self):
        assert "errors" in vvs.BASELINE_KEYS["1.0.0"]

    def test_baseline_keys_nonempty(self):
        for version, keys in vvs.BASELINE_KEYS.items():
            assert len(keys) > 0, f"version {version} has empty key set"


class TestMainUnknownVersion:
    def test_unknown_version_returns_2(self):
        result = vvs.main.__wrapped__ if hasattr(vvs.main, "__wrapped__") else None
        with patch("sys.argv", ["prog", "--compat", "99.99.99"]):
            rc = vvs.main()
        assert rc == 2


class TestMainCollectorFails:
    def test_nonzero_returncode_returns_2(self):
        bad_result = _make_run_result(returncode=1, stdout="", stderr="error")
        with patch("subprocess.run", return_value=bad_result), \
             patch("sys.argv", ["prog", "--compat", "1.0.0"]):
            rc = vvs.main()
        assert rc == 2

    def test_empty_stdout_returns_2(self):
        bad_result = _make_run_result(returncode=0, stdout="   ", stderr="")
        with patch("subprocess.run", return_value=bad_result), \
             patch("sys.argv", ["prog", "--compat", "1.0.0"]):
            rc = vvs.main()
        assert rc == 2

    def test_invalid_json_returns_2(self):
        bad_result = _make_run_result(returncode=0, stdout="not json {{{", stderr="")
        with patch("subprocess.run", return_value=bad_result), \
             patch("sys.argv", ["prog", "--compat", "1.0.0"]):
            rc = vvs.main()
        assert rc == 2

    def test_json_array_not_dict_returns_2(self):
        bad_result = _make_run_result(returncode=0, stdout=json.dumps([1, 2, 3]), stderr="")
        with patch("subprocess.run", return_value=bad_result), \
             patch("sys.argv", ["prog", "--compat", "1.0.0"]):
            rc = vvs.main()
        assert rc == 2

    def test_timeout_returns_2(self):
        import subprocess
        with patch("subprocess.run", side_effect=subprocess.TimeoutExpired("cmd", 60)), \
             patch("sys.argv", ["prog", "--compat", "1.0.0"]):
            rc = vvs.main()
        assert rc == 2


class TestMainKeysMissing:
    def test_missing_key_returns_1(self):
        payload = {k: None for k in vvs.BASELINE_KEYS["1.0.0"]}
        del payload["heartbeat"]
        good_result = _make_run_result(returncode=0, stdout=json.dumps(payload))
        with patch("subprocess.run", return_value=good_result), \
             patch("sys.argv", ["prog", "--compat", "1.0.0"]):
            rc = vvs.main()
        assert rc == 1

    def test_all_missing_returns_1(self):
        good_result = _make_run_result(returncode=0, stdout=json.dumps({"only_new_key": 1}))
        with patch("subprocess.run", return_value=good_result), \
             patch("sys.argv", ["prog", "--compat", "1.0.0"]):
            rc = vvs.main()
        assert rc == 1


class TestMainSuccess:
    def test_all_keys_present_returns_0(self):
        payload = {k: None for k in vvs.BASELINE_KEYS["1.0.0"]}
        good_result = _make_run_result(returncode=0, stdout=json.dumps(payload))
        with patch("subprocess.run", return_value=good_result), \
             patch("sys.argv", ["prog", "--compat", "1.0.0"]):
            rc = vvs.main()
        assert rc == 0

    def test_extra_keys_allowed(self):
        payload = {k: None for k in vvs.BASELINE_KEYS["1.0.0"]}
        payload["new_key_added_later"] = "value"
        payload["another_new_key"] = 42
        good_result = _make_run_result(returncode=0, stdout=json.dumps(payload))
        with patch("subprocess.run", return_value=good_result), \
             patch("sys.argv", ["prog", "--compat", "1.0.0"]):
            rc = vvs.main()
        assert rc == 0
