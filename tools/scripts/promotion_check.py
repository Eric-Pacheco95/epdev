#!/usr/bin/env python3
"""Promotion check -- scan synthesis themes and propose wisdom promotions.

Scans memory/learning/synthesis/ for established/proven themes and generates
promotion proposals to data/promotion_proposals.json.  Proposals are staged
for Eric's review via /vitals morning brief.

Usage:
    python tools/scripts/promotion_check.py               # check + propose
    python tools/scripts/promotion_check.py --stats        # counts only
    python tools/scripts/promotion_check.py --approve <id> # promote a proposal
    python tools/scripts/promotion_check.py --approve-all  # promote all pending
    python tools/scripts/promotion_check.py --json         # machine output

Routing rules:
    domain-insight  -> memory/learning/wisdom/{topic}.md   (auto on approve)
    identity/goal   -> TELOS update proposal               (requires /telos-update)
    behavioral      -> steering rule proposal              (requires /update-steering-rules)
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import datetime
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
SYNTHESIS_DIR = REPO_ROOT / "memory" / "learning" / "synthesis"
WISDOM_DIR = REPO_ROOT / "memory" / "learning" / "wisdom"
PROPOSALS_FILE = REPO_ROOT / "data" / "promotion_proposals.json"
DECISIONS_DIR = REPO_ROOT / "history" / "decisions"

MIN_SYNTHESIS_DOCS = 15


# -- Parsing ------------------------------------------------------------------

def _parse_themes(synthesis_path: Path) -> list[dict]:
    """Extract themes from a single synthesis markdown file."""
    text = synthesis_path.read_text(encoding="utf-8", errors="replace")
    themes = []
    current = None

    for line in text.splitlines():
        # Theme header
        m = re.match(r"^### Theme:\s*(.+)$", line)
        if m:
            if current:
                themes.append(current)
            current = {
                "name": m.group(1).strip(),
                "source_file": synthesis_path.name,
                "source_path": str(synthesis_path),
                "maturity": "candidate",
                "confidence": 0,
                "anti_pattern": False,
                "supporting_signals": [],
                "pattern": "",
                "implication": "",
                "action": "",
            }
            continue

        if current is None:
            continue

        # Key-value fields
        if line.startswith("- Maturity:"):
            current["maturity"] = line.split(":", 1)[1].strip()
        elif line.startswith("- Confidence:"):
            try:
                current["confidence"] = int(
                    re.search(r"(\d+)", line).group(1)
                )
            except (AttributeError, ValueError):
                pass
        elif line.startswith("- Anti-pattern:"):
            current["anti_pattern"] = "true" in line.lower()
        elif line.startswith("- Supporting signals:"):
            sigs = line.split(":", 1)[1].strip()
            current["supporting_signals"] = [
                s.strip().strip("`") for s in sigs.split(",") if s.strip()
            ]
        elif line.startswith("- Pattern:"):
            current["pattern"] = line.split(":", 1)[1].strip()
        elif line.startswith("- Implication:"):
            current["implication"] = line.split(":", 1)[1].strip()
        elif line.startswith("- Action:"):
            current["action"] = line.split(":", 1)[1].strip()

    if current:
        themes.append(current)

    return themes


def _classify_route(theme: dict) -> str:
    """Determine promotion route based on theme content."""
    name_lower = theme["name"].lower()
    pattern_lower = theme.get("pattern", "").lower()
    implication_lower = theme.get("implication", "").lower()

    # Identity/goal indicators
    identity_keywords = [
        "telos", "identity", "goal", "mission", "belief",
        "value", "purpose", "strategy", "vision",
    ]
    if any(kw in name_lower or kw in implication_lower for kw in identity_keywords):
        return "telos"

    # Behavioral pattern indicators
    behavioral_keywords = [
        "steering", "rule", "workflow", "discipline", "constraint",
        "must", "never", "always", "should not", "avoid",
        "behavioral", "habit", "pattern",
    ]
    if any(kw in name_lower or kw in implication_lower or kw in pattern_lower
           for kw in behavioral_keywords):
        return "steering"

    # Default: domain insight -> wisdom
    return "wisdom"


# -- Proposal management ------------------------------------------------------

def _load_proposals() -> list[dict]:
    """Load existing proposals from disk."""
    if PROPOSALS_FILE.exists():
        try:
            return json.loads(PROPOSALS_FILE.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            return []
    return []


def _save_proposals(proposals: list[dict]) -> None:
    """Write proposals to disk."""
    PROPOSALS_FILE.parent.mkdir(parents=True, exist_ok=True)
    PROPOSALS_FILE.write_text(
        json.dumps(proposals, indent=2, ensure_ascii=True) + "\n",
        encoding="utf-8",
    )


def _proposal_id(theme_name: str, source_file: str) -> str:
    """Stable ID for dedup."""
    slug = re.sub(r"[^a-z0-9]+", "-", theme_name.lower()).strip("-")
    return f"{source_file}:{slug}"


def _is_already_promoted(proposal_id: str, proposals: list[dict]) -> bool:
    """Check if a theme has already been promoted."""
    for p in proposals:
        if p.get("id") == proposal_id and p.get("status") == "promoted":
            return True
    return False


# -- Core logic ---------------------------------------------------------------

def check_promotions(verbose: bool = True) -> dict:
    """Scan synthesis docs and generate promotion proposals.

    Returns {synthesis_count, themes_found, proposals_generated, proposals_skipped}.
    """
    if not SYNTHESIS_DIR.exists():
        if verbose:
            print("No synthesis directory found.")
        return {"synthesis_count": 0, "themes_found": 0,
                "proposals_generated": 0, "proposals_skipped": 0}

    synth_files = sorted(SYNTHESIS_DIR.glob("*.md"))
    synthesis_count = len(synth_files)

    if synthesis_count < MIN_SYNTHESIS_DOCS:
        if verbose:
            print(f"Only {synthesis_count} synthesis docs (need {MIN_SYNTHESIS_DOCS}). "
                  f"Promotion check deferred.")
        return {"synthesis_count": synthesis_count, "themes_found": 0,
                "proposals_generated": 0, "proposals_skipped": 0}

    # Parse all themes across all synthesis docs
    all_themes = []
    for sf in synth_files:
        all_themes.extend(_parse_themes(sf))

    # Filter to promotable themes (established or proven, not anti-pattern)
    promotable = [
        t for t in all_themes
        if t["maturity"] in ("established", "proven") and not t["anti_pattern"]
    ]

    existing_proposals = _load_proposals()
    new_proposals = []
    skipped = 0

    for theme in promotable:
        pid = _proposal_id(theme["name"], theme["source_file"])

        # Skip if already proposed or promoted
        if any(p["id"] == pid for p in existing_proposals):
            skipped += 1
            continue

        route = _classify_route(theme)
        proposal = {
            "id": pid,
            "theme_name": theme["name"],
            "source_file": theme["source_file"],
            "maturity": theme["maturity"],
            "confidence": theme["confidence"],
            "route": route,
            "supporting_signals": theme["supporting_signals"],
            "pattern": theme["pattern"],
            "implication": theme["implication"],
            "action": theme["action"],
            "status": "pending",
            "proposed_at": datetime.now().strftime("%Y-%m-%dT%H:%M:%S"),
        }
        new_proposals.append(proposal)

    if new_proposals:
        all_proposals = existing_proposals + new_proposals
        _save_proposals(all_proposals)
        if verbose:
            print(f"Generated {len(new_proposals)} new proposal(s):")
            for p in new_proposals:
                print(f"  [{p['route']}] {p['theme_name']} "
                      f"({p['maturity']}, {p['confidence']}%)")

    if verbose and skipped:
        print(f"Skipped {skipped} already-proposed theme(s).")

    return {
        "synthesis_count": synthesis_count,
        "themes_found": len(all_themes),
        "proposals_generated": len(new_proposals),
        "proposals_skipped": skipped,
    }


def get_pending_proposals() -> list[dict]:
    """Return proposals with status=pending."""
    return [p for p in _load_proposals() if p.get("status") == "pending"]


def approve_proposal(proposal_id: str, verbose: bool = True) -> bool:
    """Approve and execute a single promotion proposal.

    Returns True on success.
    """
    proposals = _load_proposals()
    target = None
    for p in proposals:
        if p["id"] == proposal_id:
            target = p
            break

    if target is None:
        if verbose:
            print(f"Proposal not found: {proposal_id}")
        return False

    if target["status"] == "promoted":
        if verbose:
            print(f"Already promoted: {target['theme_name']}")
        return False

    route = target["route"]
    success = False

    if route == "wisdom":
        success = _promote_to_wisdom(target, verbose)
        if success:
            target["status"] = "promoted"
            target["promoted_at"] = datetime.now().strftime("%Y-%m-%dT%H:%M:%S")
    elif route == "telos":
        # Stage only -- requires /telos-update
        target["status"] = "staged-telos"
        if verbose:
            print(f"Staged for TELOS update: {target['theme_name']}")
            print("  Run /telos-update to apply.")
        success = True
    elif route == "steering":
        # Stage only -- requires /update-steering-rules
        target["status"] = "staged-steering"
        if verbose:
            print(f"Staged for steering rule: {target['theme_name']}")
            print("  Run /update-steering-rules to apply.")
        success = True

    if success:
        _write_audit_trail(target)
        _save_proposals(proposals)

    return success


def _promote_to_wisdom(proposal: dict, verbose: bool = True) -> bool:
    """Write a wisdom article from a promotion proposal."""
    WISDOM_DIR.mkdir(parents=True, exist_ok=True)

    slug = re.sub(r"[^a-z0-9]+", "-", proposal["theme_name"].lower()).strip("-")
    filename = f"{slug}.md"
    filepath = WISDOM_DIR / filename

    if filepath.exists():
        if verbose:
            print(f"Wisdom file already exists: {filepath}")
        return False

    signals_list = "\n".join(
        f"  - `{s}`" for s in proposal.get("supporting_signals", [])
    )

    # Sanitize content fields (synthesis is self-authored but defense-in-depth)
    def _safe(text: str) -> str:
        return re.sub(
            r"(?i)(ignore\s+all\s+previous|you\s+are\s+now|<\s*/?system\s*>)",
            "[REDACTED]", text,
        )

    content = f"""# {_safe(proposal['theme_name'])}

## Pattern
{_safe(proposal.get('pattern', '(no pattern recorded)'))}

## Implication
{_safe(proposal.get('implication', '(no implication recorded)'))}

## Recommended Action
{_safe(proposal.get('action', '(no action recorded)'))}

## Source Lineage
- Synthesis: `{proposal.get('source_file', 'unknown')}`
- Maturity: {proposal.get('maturity', 'unknown')} ({proposal.get('confidence', 0)}%)
- Promoted: {datetime.now().strftime('%Y-%m-%d')}
- Supporting signals:
{signals_list}
"""

    filepath.write_text(content, encoding="utf-8")
    if verbose:
        print(f"Promoted to wisdom: {filepath}")
    return True


def _write_audit_trail(proposal: dict) -> None:
    """Write a decision record for the promotion."""
    DECISIONS_DIR.mkdir(parents=True, exist_ok=True)
    today = datetime.now().strftime("%Y-%m-%d")
    slug = re.sub(r"[^a-z0-9]+", "-", proposal["theme_name"].lower()).strip("-")[:60]
    filepath = DECISIONS_DIR / f"{today}_promote-{slug}.md"

    content = f"""# Decision: Promote theme to {proposal['route']}

- Date: {today}
- Theme: {proposal['theme_name']}
- Route: {proposal['route']}
- Maturity: {proposal['maturity']} ({proposal['confidence']}%)
- Source: {proposal.get('source_file', 'unknown')}

## Context
Theme reached {proposal['maturity']} maturity with {len(proposal.get('supporting_signals', []))} supporting signals.

## Decision
Approved for promotion via {proposal['route']} route.

## Outcome
{"Written to memory/learning/wisdom/" if proposal['route'] == 'wisdom' else "Staged for manual application via " + ('telos-update' if proposal['route'] == 'telos' else 'update-steering-rules')}
"""

    filepath.write_text(content, encoding="utf-8")


# -- CLI ----------------------------------------------------------------------

def main() -> int:
    parser = argparse.ArgumentParser(description="Jarvis wisdom promotion check")
    parser.add_argument("--stats", action="store_true",
                        help="Show counts only")
    parser.add_argument("--json", action="store_true",
                        help="Machine-readable output")
    parser.add_argument("--approve", type=str, default=None,
                        help="Approve a specific proposal by ID")
    parser.add_argument("--approve-all", action="store_true",
                        help="Approve all pending proposals")
    parser.add_argument("--pending", action="store_true",
                        help="List pending proposals")
    args = parser.parse_args()

    if args.approve:
        ok = approve_proposal(args.approve, verbose=not args.json)
        if args.json:
            print(json.dumps({"approved": ok, "id": args.approve}))
        return 0 if ok else 1

    if args.approve_all:
        pending = get_pending_proposals()
        results = []
        for p in pending:
            ok = approve_proposal(p["id"], verbose=not args.json)
            results.append({"id": p["id"], "approved": ok})
        if args.json:
            print(json.dumps(results, indent=2))
        else:
            print(f"Approved {sum(1 for r in results if r['approved'])} of {len(results)}")
        return 0

    if args.pending:
        pending = get_pending_proposals()
        if args.json:
            print(json.dumps(pending, indent=2))
        else:
            if not pending:
                print("No pending proposals.")
            else:
                print(f"{len(pending)} pending proposal(s):")
                for p in pending:
                    print(f"  [{p['route']}] {p['theme_name']} "
                          f"({p['maturity']}, {p['confidence']}%)")
                    print(f"    ID: {p['id']}")
        return 0

    result = check_promotions(verbose=not args.json)

    if args.json or args.stats:
        print(json.dumps(result, indent=2))

    return 0


if __name__ == "__main__":
    sys.exit(main())
