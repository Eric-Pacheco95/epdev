#!/usr/bin/env python3
"""Ceremony Tier -- composite the 4 Task Typing axes into one routing scalar.

Formula: tier = sum(axis matches the unfavorable value).

Unfavorable values per axis:
    stakes:        high
    ambiguity:     high
    solvability:   low
    verifiability: low

Range: 0 (all favorable) .. 4 (all unfavorable).

Tier banding (drives behavior in orchestration/steering/ceremony-tier.md):
    T0    = tier 0      no ceremony
    T1-2  = tier 1 or 2 standard ceremony
    T3-4  = tier 3 or 4 hard halts at phase boundaries

Missing-axis policy (deterministic):
    - Frontmatter absent entirely         -> raise MissingFrontmatterError
    - Axis missing within frontmatter     -> default to "medium" (favorable)
    - Invalid value (e.g. "critical")     -> raise InvalidAxisValueError

Usage:
    python tools/scripts/ceremony_tier.py \
        --axes stakes=high,ambiguity=low,solvability=high,verifiability=high
    -> 1

    python tools/scripts/ceremony_tier.py --prd memory/work/foo/PRD.md
    -> 2

    python tools/scripts/ceremony_tier.py --prd PATH --json
    -> {"tier": 2, "band": "T1-2", "axes": {...}, "axis_default_used": ["solvability"]}

Exit codes:
    0 = tier computed successfully (printed to stdout)
    1 = invalid axis value or unparseable input
    2 = frontmatter absent (PRD has no axis labels)
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]

FOUR_AXES = ("stakes", "ambiguity", "solvability", "verifiability")
VALID_AXIS_VALUES = {"low", "medium", "high"}
UNFAVORABLE = {
    "stakes": "high",
    "ambiguity": "high",
    "solvability": "low",
    "verifiability": "low",
}


class MissingFrontmatterError(Exception):
    """Raised when frontmatter block is entirely absent (no `---` delimiters)."""


class InvalidAxisValueError(Exception):
    """Raised when an axis has a non-canonical value (e.g. `stakes: critical`)."""


def compute_tier(axes: dict) -> tuple[int, list[str]]:
    """Compute ceremony tier from a 4-axis dict.

    Args:
        axes: dict with keys (subset of) FOUR_AXES; values must be one of
              VALID_AXIS_VALUES if present.

    Returns:
        (tier, axis_default_used) where axis_default_used lists axes that
        were absent and silently defaulted to "medium" for the calculation.

    Raises:
        InvalidAxisValueError: any present axis has a value outside
            {"low", "medium", "high"}.
    """
    if not isinstance(axes, dict):
        raise InvalidAxisValueError(f"axes must be a dict, got {type(axes).__name__}")

    defaults_used: list[str] = []
    resolved: dict[str, str] = {}
    for axis in FOUR_AXES:
        val = axes.get(axis)
        if val is None or val == "":
            resolved[axis] = "medium"
            defaults_used.append(axis)
            continue
        if val not in VALID_AXIS_VALUES:
            raise InvalidAxisValueError(
                f"{axis}={val!r} -- must be one of {sorted(VALID_AXIS_VALUES)}"
            )
        resolved[axis] = val

    tier = sum(1 for axis in FOUR_AXES if resolved[axis] == UNFAVORABLE[axis])
    return tier, defaults_used


def band_for_tier(tier: int) -> str:
    """Map raw tier (0-4) to behavioral band."""
    if tier == 0:
        return "T0"
    if tier in (1, 2):
        return "T1-2"
    if tier in (3, 4):
        return "T3-4"
    raise ValueError(f"tier out of range: {tier}")


def parse_axes_arg(raw: str) -> dict:
    """Parse --axes 'stakes=high,ambiguity=low,...' into a dict."""
    out: dict[str, str] = {}
    for chunk in raw.split(","):
        chunk = chunk.strip()
        if not chunk:
            continue
        if "=" not in chunk:
            raise InvalidAxisValueError(f"axis pair missing '=': {chunk!r}")
        k, _, v = chunk.partition("=")
        out[k.strip()] = v.strip()
    return out


def axes_from_prd(prd_path: Path) -> dict:
    """Load 4-axis values from a PRD's frontmatter.

    Reuses isc_validator.check_frontmatter_axes() so the parsing logic is
    single-sourced.
    """
    sys.path.insert(0, str(REPO_ROOT))
    from tools.scripts.isc_validator import check_frontmatter_axes  # noqa: E402

    fm = check_frontmatter_axes(prd_path)
    if fm["grandfathered"] or not fm["has_frontmatter"]:
        raise MissingFrontmatterError(
            f"{prd_path}: no frontmatter block; cannot derive ceremony tier"
        )
    if fm["four_axis"]["invalid"]:
        bad = fm["four_axis"]["invalid"]
        raise InvalidAxisValueError(
            f"{prd_path}: invalid axis values: {bad}"
        )
    return {a: v for a, v in fm["values"].items() if v}


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Compute ceremony tier from the 4 Task Typing axes"
    )
    src = parser.add_mutually_exclusive_group(required=True)
    src.add_argument(
        "--axes",
        type=str,
        help="Comma-separated axis=value pairs (e.g. stakes=high,ambiguity=low,...)",
    )
    src.add_argument("--prd", type=str, help="Path to PRD with 4-axis frontmatter")
    parser.add_argument("--json", action="store_true", help="JSON output")
    args = parser.parse_args()

    try:
        if args.axes:
            axes = parse_axes_arg(args.axes)
        else:
            prd_path = Path(args.prd)
            if not prd_path.is_absolute():
                prd_path = REPO_ROOT / prd_path
            axes = axes_from_prd(prd_path)
        tier, defaults_used = compute_tier(axes)
    except MissingFrontmatterError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2
    except InvalidAxisValueError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1

    band = band_for_tier(tier)

    if args.json:
        print(json.dumps({
            "tier": tier,
            "band": band,
            "axes": axes,
            "axis_default_used": defaults_used,
        }, sort_keys=True))
    else:
        print(tier)

    return 0


if __name__ == "__main__":
    sys.exit(main())
