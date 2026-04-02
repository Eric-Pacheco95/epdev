"""JSON output schema tests for isc_executor.py.

Verifies that --json flag emits valid, schema-conformant JSON with
required top-level fields matching the documented output contract.
"""
from __future__ import annotations

import json
import sys
import subprocess
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
EXECUTOR = REPO_ROOT / "tools" / "scripts" / "isc_executor.py"


def _write_prd(tmp_path: Path, criteria_lines: list[str]) -> Path:
    """Write a minimal PRD file with the given ISC criteria lines."""
    prd = tmp_path / "TEST_PRD.md"
    lines = ["# Test PRD\n", "\n"]
    lines.extend(line + "\n" for line in criteria_lines)
    prd.write_text("".join(lines), encoding="utf-8")
    return prd


def test_json_schema(tmp_path: Path):
    """--json emits valid JSON with _schema_version, criteria, and gate_passed."""
    prd = _write_prd(tmp_path, [
        "- [ ] The executor script exists [E] | Verify: Exist: tools/scripts/isc_executor.py",
        "- [ ] The validator script exists [E] | Verify: Exist: tools/scripts/isc_validator.py",
        "- [ ] CLAUDE.md exists [E] | Verify: Exist: CLAUDE.md",
    ])

    result = subprocess.run(
        [
            sys.executable,
            str(EXECUTOR),
            "--prd", str(prd),
            "--json",
            "--skip-format-gate",
        ],
        capture_output=True,
        text=True,
        cwd=str(REPO_ROOT),
    )

    # Must be valid JSON regardless of exit code
    try:
        data = json.loads(result.stdout)
    except json.JSONDecodeError as exc:
        pytest.fail(f"Output is not valid JSON: {exc}\nRaw stdout:\n{result.stdout[:500]}")

    # Required top-level fields
    assert "_schema_version" in data, "Missing _schema_version field"
    assert "criteria" in data, "Missing criteria field"
    assert "gate_passed" in data, "Missing gate_passed field"

    # Additional contract fields
    assert "_provenance" in data, "Missing _provenance field"
    assert "summary" in data, "Missing summary field"
    assert "prd_path" in data, "Missing prd_path field"
    assert "criteria_count" in data, "Missing criteria_count field"

    # Schema version must be a non-empty string
    assert isinstance(data["_schema_version"], str), "_schema_version must be a string"
    assert data["_schema_version"], "_schema_version must be non-empty"

    # criteria must be a list
    assert isinstance(data["criteria"], list), "criteria must be a list"

    # Each criterion must have the required fields
    for i, criterion in enumerate(data["criteria"]):
        for field in ("line", "criterion", "verify_method", "verdict", "evidence", "duration_ms"):
            assert field in criterion, f"criteria[{i}] missing field '{field}'"

    # gate_passed must be boolean
    assert isinstance(data["gate_passed"], bool), "gate_passed must be a boolean"

    # summary must have the four verdict counts
    summary = data["summary"]
    for key in ("pass", "fail", "error", "manual"):
        assert key in summary, f"summary missing '{key}' key"

    # For this PRD all files exist so gate should pass
    assert data["gate_passed"] is True, f"Expected gate_passed=True, got {data['gate_passed']}"
    assert result.returncode == 0, f"Expected exit 0, got {result.returncode}"


def test_json_provenance_fields(tmp_path: Path):
    """_provenance block contains script, version, git_hash, execution_time_ms, executed_at."""
    prd = _write_prd(tmp_path, [
        "- [ ] Executor exists [E] | Verify: Exist: tools/scripts/isc_executor.py",
        "- [ ] Validator exists [E] | Verify: Exist: tools/scripts/isc_validator.py",
        "- [ ] CLAUDE.md exists [E] | Verify: Exist: CLAUDE.md",
    ])

    result = subprocess.run(
        [
            sys.executable,
            str(EXECUTOR),
            "--prd", str(prd),
            "--json",
            "--skip-format-gate",
        ],
        capture_output=True,
        text=True,
        cwd=str(REPO_ROOT),
    )

    data = json.loads(result.stdout)
    prov = data["_provenance"]

    assert "script" in prov and "isc_executor" in prov["script"]
    assert "version" in prov
    assert "git_hash" in prov
    assert "execution_time_ms" in prov
    assert "executed_at" in prov
    assert isinstance(prov["execution_time_ms"], int)
