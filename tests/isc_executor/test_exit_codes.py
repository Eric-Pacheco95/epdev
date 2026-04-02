"""Exit code tests for isc_executor.py.

Tests verify the four exit code contract:
    0 = all non-MANUAL criteria PASS
    1 = one or more criteria FAIL
    2 = executor error
    3 = MANUAL items present, no FAILs
"""
from __future__ import annotations

import sys
import subprocess
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
EXECUTOR = REPO_ROOT / "tools" / "scripts" / "isc_executor.py"

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _run_executor(prd_path: Path) -> int:
    """Run isc_executor.py via subprocess and return its exit code."""
    result = subprocess.run(
        [sys.executable, str(EXECUTOR), "--prd", str(prd_path), "--skip-format-gate"],
        capture_output=True,
        text=True,
        cwd=str(REPO_ROOT),
    )
    return result.returncode


def _write_prd(tmp_path: Path, criteria_lines: list[str]) -> Path:
    """Write a minimal PRD file with the given ISC criteria lines."""
    prd = tmp_path / "TEST_PRD.md"
    # Wrap in enough structure to satisfy parse_isc_items -- the parser only
    # needs lines matching the "- [ ] ... | Verify:" pattern.
    lines = ["# Test PRD\n", "\n"]
    lines.extend(line + "\n" for line in criteria_lines)
    prd.write_text("".join(lines), encoding="utf-8")
    return prd


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

def test_all_pass(tmp_path: Path):
    """Exit 0 when all non-MANUAL criteria pass.

    Uses Exist: criteria pointing at files that definitely exist on this repo.
    """
    prd = _write_prd(tmp_path, [
        "- [ ] The executor script exists [E] | Verify: Exist: tools/scripts/isc_executor.py",
        "- [ ] The validator script exists [E] | Verify: Exist: tools/scripts/isc_validator.py",
        "- [ ] The CLAUDE.md root context exists [E] | Verify: Exist: CLAUDE.md",
    ])
    code = _run_executor(prd)
    assert code == 0, f"Expected exit 0 (all pass), got {code}"


def test_one_fail(tmp_path: Path):
    """Exit 1 when at least one criterion fails.

    Uses one passing Exist: criterion and one that targets a non-existent file.
    """
    prd = _write_prd(tmp_path, [
        "- [ ] The executor script exists [E] | Verify: Exist: tools/scripts/isc_executor.py",
        "- [ ] A file that does not exist [E] | Verify: Exist: this/path/does/not/exist/ever.txt",
        "- [ ] The CLAUDE.md root context exists [E] | Verify: Exist: CLAUDE.md",
    ])
    code = _run_executor(prd)
    assert code == 1, f"Expected exit 1 (fail present), got {code}"


def test_manual_no_fail(tmp_path: Path):
    """Exit 3 when MANUAL items present but no FAILs.

    Uses a Review: criterion (always MANUAL) plus passing Exist: criteria.
    """
    prd = _write_prd(tmp_path, [
        "- [ ] The executor script exists [E] | Verify: Exist: tools/scripts/isc_executor.py",
        "- [ ] Output was reviewed for correctness [E] | Verify: Review: manually inspect the table output",
        "- [ ] The CLAUDE.md root context exists [E] | Verify: Exist: CLAUDE.md",
    ])
    code = _run_executor(prd)
    assert code == 3, f"Expected exit 3 (manual present, no fail), got {code}"
