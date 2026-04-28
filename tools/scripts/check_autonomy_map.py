#!/usr/bin/env python3
"""Skill-autonomy consistency audit.

Compares three sources of truth for skill behavior gating:
  1. .claude/skills/<name>/SKILL.md     -- author intent (frontmatter + body)
  2. orchestration/routines.json        -- which skills routines route to
  3. orchestration/skill_autonomy_map.json -- gate read by task_gate.py

Detects:
  - autonomous_safe_drift   SKILL.md body declares autonomous_safe X but map says Y
  - missing_map_entry       SKILL.md exists but no entry in autonomy_map
  - orphan_map_entry        autonomy_map entry exists but SKILL.md does not
  - routine_skill_unmapped  routine references a skill not in autonomy_map
  - routine_skill_blocked   routine routes to a skill the map marks tier>2 or autonomous_safe=false
  - frontmatter_disable_routed  SKILL.md has disable-model-invocation:true but is referenced by a routine

Exits 0 always (drift is data, not a script error). Writes
data/autonomy_audit_state.json. With --notify, posts Slack alert when
findings exist.

Usage:
    python tools/scripts/check_autonomy_map.py
    python tools/scripts/check_autonomy_map.py --json
    python tools/scripts/check_autonomy_map.py --notify --write-state
    python tools/scripts/check_autonomy_map.py --self-test
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
SKILLS_DIR = REPO_ROOT / ".claude" / "skills"
AUTONOMY_MAP_PATH = REPO_ROOT / "orchestration" / "skill_autonomy_map.json"
ROUTINES_PATH = REPO_ROOT / "orchestration" / "routines.json"
STATE_PATH = REPO_ROOT / "data" / "autonomy_audit_state.json"

# Mirrors task_gate.MAX_AUTONOMOUS_TIER -- update both if changed.
MAX_AUTONOMOUS_TIER = 2

CRITICAL_TYPES = {"autonomous_safe_drift", "routine_skill_blocked", "frontmatter_disable_routed"}


def _parse_frontmatter(text: str) -> dict | None:
    """Extract YAML frontmatter as a flat dict. None if no frontmatter.

    Only handles simple `key: value` lines (no nested structures, no lists).
    Sufficient for the fields we care about (name, description,
    disable-model-invocation, user-invocable).
    """
    if not text.startswith("---\n"):
        return None
    end = text.find("\n---", 4)
    if end == -1:
        return None
    block = text[4:end]
    out: dict[str, object] = {}
    for line in block.splitlines():
        if not line.strip() or line.startswith("#"):
            continue
        if ":" not in line:
            continue
        key, _, val = line.partition(":")
        key = key.strip()
        val = val.strip().strip('"').strip("'")
        if val.lower() == "true":
            out[key] = True
        elif val.lower() == "false":
            out[key] = False
        else:
            out[key] = val
    return out


def _parse_body_autonomous_safe(text: str) -> bool | None:
    """Return the value declared under `## autonomous_safe` in the body, or None.

    Matches the SKILL.md schema convention: a `## autonomous_safe` heading
    followed by a line containing `true` or `false`.
    """
    m = re.search(
        r"^##\s+autonomous_safe\s*\n+\s*(true|false)\b",
        text,
        flags=re.MULTILINE | re.IGNORECASE,
    )
    if not m:
        return None
    return m.group(1).lower() == "true"


def _parse_skill_md(path: Path) -> dict:
    text = path.read_text(encoding="utf-8")
    fm = _parse_frontmatter(text) or {}
    body_safe = _parse_body_autonomous_safe(text)
    return {
        "name": path.parent.name,
        "frontmatter": fm,
        "body_autonomous_safe": body_safe,
        "disable_model_invocation": bool(fm.get("disable-model-invocation", False)),
    }


def _load_autonomy_map() -> dict[str, dict]:
    raw = json.loads(AUTONOMY_MAP_PATH.read_text(encoding="utf-8"))
    return {k: v for k, v in raw.items() if k != "_meta"}


def _load_routine_skill_refs() -> list[tuple[str, str, bool, bool]]:
    """Return list of (routine_id, skill_name, enabled, expects_autonomous) tuples.

    expects_autonomous is False when the task_template explicitly declares
    autonomous_safe=false -- those routines opt into the human-review path,
    so referencing a non-autonomous-safe skill is intentional, not drift.
    """
    raw = json.loads(ROUTINES_PATH.read_text(encoding="utf-8"))
    out = []
    for r in raw.get("routines", []):
        rid = r.get("routine_id", "<unknown>")
        enabled = bool(r.get("enabled", True))
        template = r.get("task_template", {})
        # Default to True: routines without an explicit autonomous_safe field
        # are assumed to expect autonomous routing.
        expects_autonomous = bool(template.get("autonomous_safe", True))
        for s in (template.get("skills") or []):
            out.append((rid, s, enabled, expects_autonomous))
    return out


def audit() -> dict:
    """Run all consistency checks. Always returns; never raises on data state."""
    findings: list[dict] = []

    autonomy_map = _load_autonomy_map()
    skill_dirs = sorted(p.parent.name for p in SKILLS_DIR.glob("*/SKILL.md"))
    skill_dir_set = set(skill_dirs)

    # 1. Orphan map entries -- map references a skill with no SKILL.md.
    for skill_name in autonomy_map:
        if skill_name not in skill_dir_set:
            findings.append({
                "type": "orphan_map_entry",
                "skill": skill_name,
                "detail": f"autonomy_map entry exists but .claude/skills/{skill_name}/SKILL.md does not",
            })

    # Parse all SKILL.md files once.
    skills_parsed: dict[str, dict] = {}
    for name in skill_dirs:
        try:
            skills_parsed[name] = _parse_skill_md(SKILLS_DIR / name / "SKILL.md")
        except Exception as exc:
            findings.append({
                "type": "skill_md_parse_error",
                "skill": name,
                "detail": str(exc),
            })

    # 2. Missing map entries + autonomous_safe drift.
    for name, parsed in skills_parsed.items():
        body_safe = parsed["body_autonomous_safe"]
        entry = autonomy_map.get(name)
        if entry is None:
            # Only flag if the skill is plausibly autonomous-eligible (has a
            # body declaration). Skills with no declaration and no entry are
            # acceptable -- they can't be routed by routines anyway because
            # task_gate blocks unmapped skills.
            if body_safe is not None:
                findings.append({
                    "type": "missing_map_entry",
                    "skill": name,
                    "detail": f"SKILL.md declares autonomous_safe={body_safe} but skill_autonomy_map.json has no entry",
                })
            continue
        map_safe = entry.get("autonomous_safe")
        if body_safe is not None and map_safe is not None and body_safe != map_safe:
            findings.append({
                "type": "autonomous_safe_drift",
                "skill": name,
                "skill_md": body_safe,
                "autonomy_map": map_safe,
                "tier": entry.get("tier"),
                "detail": "SKILL.md and autonomy_map disagree on autonomous_safe",
            })

    # 3. Routine references vs map entries.
    for rid, skill, enabled, expects_autonomous in _load_routine_skill_refs():
        if not enabled:
            continue
        entry = autonomy_map.get(skill)
        if entry is None:
            findings.append({
                "type": "routine_skill_unmapped",
                "routine": rid,
                "skill": skill,
                "detail": "routine routes to a skill not present in skill_autonomy_map.json",
            })
            continue
        if not expects_autonomous:
            # Routine explicitly declares autonomous_safe=false on its task
            # template -- it opts into the human-review path, so a tier>2 or
            # autonomous_safe=false skill reference is intentional.
            continue
        tier = entry.get("tier", 99)
        if tier > MAX_AUTONOMOUS_TIER or not entry.get("autonomous_safe"):
            findings.append({
                "type": "routine_skill_blocked",
                "routine": rid,
                "skill": skill,
                "tier": tier,
                "autonomous_safe": entry.get("autonomous_safe"),
                "detail": f"routine claims autonomous but references skill task_gate will block (tier>{MAX_AUTONOMOUS_TIER} or autonomous_safe=false)",
            })

    # 4. Frontmatter disable-model-invocation vs routine routing.
    routine_skills = {s for _, s, e, _exp in _load_routine_skill_refs() if e}
    for name, parsed in skills_parsed.items():
        if parsed["disable_model_invocation"] and name in routine_skills:
            findings.append({
                "type": "frontmatter_disable_routed",
                "skill": name,
                "detail": "SKILL.md has disable-model-invocation:true but is referenced by an enabled routine -- routine will fail or run unexpectedly",
            })

    state = {
        "checked_at": datetime.now(timezone.utc).isoformat(),
        "skills_checked": len(skill_dirs),
        "map_entries": len(autonomy_map),
        "findings": findings,
        "finding_count": len(findings),
        "critical_count": sum(1 for f in findings if f["type"] in CRITICAL_TYPES),
    }
    return state


def _format_slack_message(state: dict) -> str:
    findings = state["findings"]
    if not findings:
        return f"autonomy audit clean -- {state['skills_checked']} skills, {state['map_entries']} map entries, no drift"
    lines = [
        f":rotating_light: autonomy audit found {len(findings)} drift finding(s) "
        f"({state['critical_count']} critical):"
    ]
    by_type: dict[str, list[dict]] = {}
    for f in findings:
        by_type.setdefault(f["type"], []).append(f)
    for ftype, items in sorted(by_type.items()):
        marker = "  *" if ftype in CRITICAL_TYPES else "   "
        lines.append(f"{marker} `{ftype}`: {len(items)}")
        for it in items[:5]:
            label = it.get("skill") or it.get("routine") or "?"
            detail = it.get("detail", "")
            lines.append(f"      - {label}: {detail}")
        if len(items) > 5:
            lines.append(f"      ... and {len(items) - 5} more")
    lines.append(f"\nState: data/autonomy_audit_state.json")
    return "\n".join(lines)


def _self_test() -> int:
    """Smoke test: parse known files, confirm no exceptions, print summary."""
    state = audit()
    print(f"audit() returned {len(state['findings'])} findings, {state['critical_count']} critical")
    fm = _parse_frontmatter("---\nname: x\ndisable-model-invocation: true\n---\nbody")
    assert fm == {"name": "x", "disable-model-invocation": True}, f"frontmatter parse failed: {fm}"
    body = _parse_body_autonomous_safe("# h\n\n## autonomous_safe\n\nfalse\n\nmore")
    assert body is False, f"body parse failed: {body}"
    body2 = _parse_body_autonomous_safe("nothing here")
    assert body2 is None
    print("self-test PASS")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--json", action="store_true", help="emit state JSON to stdout")
    ap.add_argument("--notify", action="store_true", help="post Slack alert on findings")
    ap.add_argument("--write-state", action="store_true", help=f"write {STATE_PATH.relative_to(REPO_ROOT)}")
    ap.add_argument("--self-test", action="store_true")
    args = ap.parse_args()

    if args.self_test:
        return _self_test()

    state = audit()
    state["notified"] = False

    msg = _format_slack_message(state)

    if args.notify and state["findings"]:
        try:
            sys.path.insert(0, str(REPO_ROOT))
            from tools.scripts.slack_notify import notify  # type: ignore
            severity = "critical" if state["critical_count"] else "routine"
            notify(msg, severity=severity)
            state["notified"] = True
        except Exception as exc:
            print(f"slack notify failed: {exc}", file=sys.stderr)

    # Derive ISC pass: clean OR critical findings were notified. Written as a
    # top-level field so ISC verify can use grep (jq not always on PATH).
    state["pass"] = state["critical_count"] == 0 or state["notified"]

    if args.write_state:
        STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
        STATE_PATH.write_text(json.dumps(state, indent=2), encoding="utf-8")

    if args.json:
        print(json.dumps(state, indent=2))
    else:
        print(msg)

    # Always exit 0 -- drift findings are data, not a script error. Routine
    # ISC verifies via state file freshness, not exit code.
    return 0


if __name__ == "__main__":
    sys.exit(main())
