"""Tests for tools/scripts/financial_snapshot.py helper functions."""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from unittest.mock import patch

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

import tools.scripts.financial_snapshot as fs


class TestReadJsonIfExists:
    def test_missing_file_returns_none(self, tmp_path):
        result = fs._read_json_if_exists(tmp_path / "missing.json")
        assert result is None

    def test_valid_json_returns_dict(self, tmp_path):
        f = tmp_path / "data.json"
        f.write_text(json.dumps({"key": "value"}), encoding="utf-8")
        result = fs._read_json_if_exists(f)
        assert result == {"key": "value"}

    def test_invalid_json_returns_none(self, tmp_path):
        f = tmp_path / "bad.json"
        f.write_text("not valid json", encoding="utf-8")
        result = fs._read_json_if_exists(f)
        assert result is None

    def test_max_bytes_truncation(self, tmp_path):
        f = tmp_path / "big.json"
        large = json.dumps({"data": "x" * 10000})
        f.write_text(large, encoding="utf-8")
        result = fs._read_json_if_exists(f, max_bytes=50)
        assert result is None

    def test_empty_file_returns_none(self, tmp_path):
        f = tmp_path / "empty.json"
        f.write_text("", encoding="utf-8")
        result = fs._read_json_if_exists(f)
        assert result is None


class TestCollectCryptoPayload:
    def test_missing_root_dir(self, tmp_path, monkeypatch):
        monkeypatch.setenv("CRYPTO_BOT_ROOT", str(tmp_path / "nonexistent"))
        monkeypatch.delenv("CRYPTO_BOT_FINANCIAL_FILES", raising=False)
        result = fs._collect_crypto_payload()
        assert result["root_exists"] is False
        assert result["files"] == {}

    def test_existing_root_dir(self, tmp_path, monkeypatch):
        monkeypatch.setenv("CRYPTO_BOT_ROOT", str(tmp_path))
        monkeypatch.delenv("CRYPTO_BOT_FINANCIAL_FILES", raising=False)
        result = fs._collect_crypto_payload()
        assert result["root_exists"] is True

    def test_extra_files_env_var(self, tmp_path, monkeypatch):
        data_file = tmp_path / "mydata.json"
        data_file.write_text(json.dumps({"val": 42}), encoding="utf-8")
        monkeypatch.setenv("CRYPTO_BOT_FINANCIAL_FILES", str(data_file))
        result = fs._collect_crypto_payload()
        assert str(data_file) in result["files"]
        assert result["files"][str(data_file)]["val"] == 42

    def test_missing_extra_file_not_in_result(self, tmp_path, monkeypatch):
        missing = tmp_path / "missing.json"
        monkeypatch.setenv("CRYPTO_BOT_FINANCIAL_FILES", str(missing))
        result = fs._collect_crypto_payload()
        assert str(missing) not in result["files"]

    def test_returns_root_path_string(self, tmp_path, monkeypatch):
        monkeypatch.setenv("CRYPTO_BOT_ROOT", str(tmp_path))
        monkeypatch.delenv("CRYPTO_BOT_FINANCIAL_FILES", raising=False)
        result = fs._collect_crypto_payload()
        assert "root" in result
        assert isinstance(result["root"], str)


class TestCollectSubstack:
    def test_no_env_var_returns_none(self, monkeypatch):
        monkeypatch.delenv("SUBSTACK_REVENUE_PATH", raising=False)
        result = fs._collect_substack()
        assert result is None

    def test_empty_env_var_returns_none(self, monkeypatch):
        monkeypatch.setenv("SUBSTACK_REVENUE_PATH", "")
        result = fs._collect_substack()
        assert result is None

    def test_missing_file_returns_error(self, tmp_path, monkeypatch):
        monkeypatch.setenv("SUBSTACK_REVENUE_PATH", str(tmp_path / "missing.json"))
        result = fs._collect_substack()
        assert result is not None
        assert result.get("error") == "missing_or_invalid_json"

    def test_valid_file_returns_payload(self, tmp_path, monkeypatch):
        f = tmp_path / "revenue.json"
        f.write_text(json.dumps({"revenue": 100}), encoding="utf-8")
        monkeypatch.setenv("SUBSTACK_REVENUE_PATH", str(f))
        result = fs._collect_substack()
        assert result is not None
        assert result["payload"]["revenue"] == 100


class TestRun:
    def test_run_writes_jsonl(self, tmp_path, monkeypatch):
        out_file = tmp_path / "snapshot.jsonl"
        monkeypatch.setattr(fs, "OUT_FILE", out_file)
        monkeypatch.setattr(fs, "OUT_DIR", tmp_path)
        monkeypatch.delenv("CRYPTO_BOT_FINANCIAL_FILES", raising=False)
        row = fs.run()
        assert out_file.exists()
        written = json.loads(out_file.read_text().strip())
        assert "ts" in written
        assert "crypto_bot" in written

    def test_run_returns_dict(self, tmp_path, monkeypatch):
        monkeypatch.setattr(fs, "OUT_FILE", tmp_path / "snapshot.jsonl")
        monkeypatch.setattr(fs, "OUT_DIR", tmp_path)
        monkeypatch.delenv("CRYPTO_BOT_FINANCIAL_FILES", raising=False)
        result = fs.run()
        assert isinstance(result, dict)
        assert "ts" in result

    def test_run_appends_multiple_rows(self, tmp_path, monkeypatch):
        out_file = tmp_path / "snapshot.jsonl"
        monkeypatch.setattr(fs, "OUT_FILE", out_file)
        monkeypatch.setattr(fs, "OUT_DIR", tmp_path)
        monkeypatch.delenv("CRYPTO_BOT_FINANCIAL_FILES", raising=False)
        fs.run()
        fs.run()
        lines = [l for l in out_file.read_text().splitlines() if l.strip()]
        assert len(lines) == 2
