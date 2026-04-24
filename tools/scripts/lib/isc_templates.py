"""isc_templates -- deterministic ISC strings from structured gap kinds (5C-5C).

Gap kinds: add_tests, fix_lint, remove_dead_code, update_docs.

Production presets (research, overnight, producers) live in this module so
dispatcher tasks share one source of truth. Usage is appended to
data/isc_template_usage.jsonl when JARVIS_ISC_TEMPLATE_LOG is unset or 1.

Each criterion uses `| Verify:` commands compatible with isc_common (allowlisted
shell + `python tools/scripts/...` helpers). Callers should pass repo-relative
POSIX paths (forward slashes, no spaces) for reliable autonomous verify.
"""
from __future__ import annotations

import json
import os
import re
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[3]
USAGE_LOG = REPO_ROOT / "data" / "isc_template_usage.jsonl"

_ANCHOR_TOKEN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.:-]*$")

# Public gap kind identifiers (tasklist 5C-5C)
GAP_ADD_TESTS = "add_tests"
GAP_FIX_LINT = "fix_lint"
GAP_REMOVE_DEAD_CODE = "remove_dead_code"
GAP_UPDATE_DOCS = "update_docs"

GAP_KINDS = frozenset({
    GAP_ADD_TESTS,
    GAP_FIX_LINT,
    GAP_REMOVE_DEAD_CODE,
    GAP_UPDATE_DOCS,
})


class UnsafePathError(ValueError):
    """Raised when a path is not safe to embed in an ISC verify command."""


def _usage_logging_enabled() -> bool:
    return os.environ.get("JARVIS_ISC_TEMPLATE_LOG", "1").strip().lower() not in (
        "0",
        "false",
        "no",
    )


def log_preset_use(preset: str, **meta: Any) -> None:
    """Append one monitoring row (JSONL) for production preset usage."""
    if not _usage_logging_enabled():
        return
    row = {
        "ts": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "preset": preset,
        "meta": meta,
    }
    try:
        USAGE_LOG.parent.mkdir(parents=True, exist_ok=True)
        with open(USAGE_LOG, "a", encoding="utf-8") as f:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")
    except OSError:
        pass


def _finalize(lines: list[str], preset: str, **meta: Any) -> list[str]:
    log_preset_use(preset, **meta)
    return lines


def normalize_repo_rel_path(path: str) -> str:
    """Return POSIX repo-relative path, or raise if unsafe.

    Rejects absolute paths, empty strings, and `..` segments (injection / escape).
    """
    if not path or not isinstance(path, str):
        raise UnsafePathError("path must be a non-empty string")
    cleaned = path.strip().replace("\\", "/").lstrip("/")
    parts = PurePosixPath(cleaned).parts
    if ".." in parts:
        raise UnsafePathError("path must not contain '..'")
    if not parts:
        raise UnsafePathError("path is empty after normalization")
    return str(PurePosixPath(*parts))


def isc_add_tests(test_file: str, impl_file: str | None = None) -> list[str]:
    """ISC for adding tests: test module exists and defines at least one test."""
    tf = normalize_repo_rel_path(test_file)
    lines = [
        f"Test module exists | Verify: test -f {tf}",
        f"Test module defines at least one test_ function | Verify: grep -q '^def test_' {tf}",
    ]
    if impl_file:
        impl = normalize_repo_rel_path(impl_file)
        lines.insert(
            0,
            f"Implementation module still present | Verify: test -f {impl}",
        )
    return lines


def isc_fix_lint(target_file: str) -> list[str]:
    """ISC for lint/style fix: file exists and Python compiles."""
    tf = normalize_repo_rel_path(target_file)
    return [
        f"Target file exists | Verify: test -f {tf}",
        f"Target file is valid Python (syntax) | Verify: python tools/scripts/verify_py_compile.py {tf}",
    ]


def isc_remove_dead_code(removed_rel_path: str) -> list[str]:
    """ISC for deleting dead code: path must be gone from repo."""
    rp = normalize_repo_rel_path(removed_rel_path)
    return [
        f"Removed path is absent from repo | Verify: python tools/scripts/verify_repo_path_absent.py {rp}",
    ]


def isc_update_docs(doc_file: str, anchor_substring: str) -> list[str]:
    """ISC for documentation update: file exists and contains an anchor phrase.

    anchor_substring must be a short literal (no shell metacharacters); prefer
    single-token anchors when possible.
    """
    df = normalize_repo_rel_path(doc_file)
    if not anchor_substring or not anchor_substring.strip():
        raise UnsafePathError("anchor_substring required")
    anchor = anchor_substring.strip()
    if not _ANCHOR_TOKEN.match(anchor):
        raise UnsafePathError(
            "anchor_substring must be a single shell-safe token "
            "(letters, digits, ._:-); use a unique heading slug or tag"
        )
    return [
        f"Doc file exists | Verify: test -f {df}",
        f"Doc contains required anchor | Verify: grep -q {anchor} {df}",
    ]


def isc_from_gap(kind: str, **kwargs) -> list[str]:
    """Build ISC list for a gap kind. Raises ValueError/UnsafePathError on bad input."""
    if kind not in GAP_KINDS:
        raise ValueError(f"unknown gap kind {kind!r}; expected one of {sorted(GAP_KINDS)}")
    if kind == GAP_ADD_TESTS:
        impl = kwargs.get("impl_file")
        lines = isc_add_tests(kwargs["test_file"], impl_file=impl)
    elif kind == GAP_FIX_LINT:
        lines = isc_fix_lint(kwargs["target_file"])
    elif kind == GAP_REMOVE_DEAD_CODE:
        lines = isc_remove_dead_code(kwargs["removed_path"])
    elif kind == GAP_UPDATE_DOCS:
        lines = isc_update_docs(kwargs["doc_file"], kwargs["anchor_substring"])
    else:
        raise AssertionError("unreachable")
    meta = {k: str(v) for k, v in kwargs.items()}
    return _finalize(lines, f"gap:{kind}", **meta)


# -- Production presets (producers / overnight) --------------------------------


def isc_research_topic(slug: str, domain: str) -> list[str]:
    """ISC lines for research_producer autonomous research tasks."""
    slug = slug.strip()
    domain = domain.strip()
    slug_key = slug[:30]
    lines = [
        f"Research brief exists | Verify: test -f memory/work/{slug}/research_brief.md",
        f"Domain knowledge article filed | Verify: find memory/knowledge/{domain} -name '*{slug_key}*.md'",
    ]
    return _finalize(lines, "research_topic", slug=slug, domain=domain)


def isc_overnight_branch_review(branch: str) -> list[str]:
    """ISC for overnight_runner branch review pending_review tasks."""
    lines = [
        f"Overnight branch {branch} reviewed and merged or rejected "
        f"| Verify: Review git log --oneline {branch}",
    ]
    return _finalize(lines, "overnight_branch_review", branch=branch)


def isc_autoresearch_proposals_review() -> list[str]:
    """ISC for jarvis_autoresearch backlog injection."""
    lines = [
        "Each proposal is either accepted (action taken), deferred "
        "with rationale, or rejected "
        "| Verify: Review",
    ]
    return _finalize(lines, "autoresearch_proposals")


def isc_producer_recency(entry_name: str) -> list[str]:
    """ISC for collect_producer_recency watchdog tasks."""
    lines = [
        "Root cause of %s staleness is identified | Verify: Review" % entry_name,
        "Producer is either fixed, schedule is corrected, or the "
        "producers.json entry is updated/removed | Verify: Review",
    ]
    return _finalize(lines, "producer_recency", entry=entry_name)


def isc_isc_producer_ready_to_mark() -> list[str]:
    lines = [
        "All ready_to_mark criteria are checked off in their PRDs | Verify: Review",
    ]
    return _finalize(lines, "isc_producer_ready_to_mark")


def isc_isc_producer_fail_batch() -> list[str]:
    lines = [
        "Each failing criterion is either fixed, marked deferred, "
        "or has its verify method corrected | Verify: Review",
    ]
    return _finalize(lines, "isc_producer_fail_batch")


def isc_paradigm_degraded(label: str, threshold: float) -> list[str]:
    """ISC for paradigm_health degraded paradigm tasks."""
    lines = [
        f"{label} health score >= {threshold:.2f} "
        f"| Verify: Review paradigm_health.py output",
    ]
    return _finalize(lines, "paradigm_degraded", label=label, threshold=threshold)


def isc_security_scan_review() -> list[str]:
    lines = [
        "Each finding is either remediated, accepted with a "
        "documented exception, or flagged as a false positive "
        "| Verify: Review",
    ]
    return _finalize(lines, "security_scan_review")


def isc_prediction_backtest_followup() -> list[str]:
    """ISC for prediction_event_generator chained backtest task."""
    lines = [
        "At least 1 new backtest prediction file written | Verify: Glob data/predictions/backtest/*.md and confirm at least one file exists",
        "backtest_state.json updated with new run entries | Verify: Read data/backtest_state.json and confirm 'completed' dict has entries",
    ]
    return _finalize(lines, "prediction_backtest_followup")
