#!/usr/bin/env python3
"""dream.py -- Jarvis memory consolidation worker.

Runs the 4-phase AutoDream cycle over Jarvis memory files:
  Phase 1: Orient      -- inventory scope, check lock, last-run timestamp
  Phase 2: Gather      -- semantic duplicate scan, stale pointer check, relative date grep
  Phase 3: Consolidate -- auto-merge duplicates (with snapshots), fix dates, remove stale ptrs
  Phase 4: Prune+Index -- rebuild MEMORY.md, update embedding index, write log + health signal

Fully autonomous: acts first, reports after. Eric reviews data/dream_last_report.md.
Snapshots written before every destructive write -- revert via snapshot or git.

Usage:
    python tools/scripts/dream.py              # full run, print report
    python tools/scripts/dream.py --dry-run    # show what would change, no writes
    python tools/scripts/dream.py --autonomous # overnight mode: suppress prompts, write report only

Outputs:
    data/dream.lock                  -- concurrency lock (auto-cleared)
    data/dream_last_run.txt          -- ISO timestamp of last successful run
    data/dream_last_report.md        -- human-readable report of what changed
    data/dream_snapshots/            -- pre-merge snapshots for rollback
    history/changes/dream_log.md     -- append-only audit trail
    memory/learning/signals/         -- health signal on completion
"""

from __future__ import annotations

import argparse
import os
import re
import shutil
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from jarvis_config import PROTECTED_FILES, is_protected  # noqa: E402

# --- Paths ---

REPO_ROOT = Path(__file__).resolve().parents[2]
MEMORY_DIR = (
    Path.home()
    / ".claude"
    / "projects"
    / "C--Users-ericp-Github-epdev"
    / "memory"
)
MEMORY_INDEX = MEMORY_DIR / "MEMORY.md"
DATA_DIR = REPO_ROOT / "data"
LOCK_FILE = DATA_DIR / "dream.lock"
LAST_RUN_FILE = DATA_DIR / "dream_last_run.txt"
REPORT_FILE = DATA_DIR / "dream_last_report.md"
SNAPSHOTS_DIR = DATA_DIR / "dream_snapshots"
DREAM_LOG = REPO_ROOT / "history" / "changes" / "dream_log.md"
SIGNALS_DIR = REPO_ROOT / "memory" / "learning" / "signals"
SYNTHESIS_DIR = REPO_ROOT / "memory" / "learning" / "synthesis"

MEMORY_INDEX_MAX_LINES = 200
LOCK_STALE_SECONDS = 7200  # 2 hours

# Phase 2 promotion thresholds
PROMOTION_MATURITY = "proven"        # must match exactly
PROMOTION_MIN_CONFIDENCE = 90        # must be >= this %
PROMOTION_MAX_SIMILARITY = 0.85      # theme must NOT already exist in auto-memory (floor ~0.75 for unrelated content)

# Type inference keyword maps (checked against theme name + implication text)
TYPE_SIGNALS = {
    "project": [
        "pipeline", "architecture", "phase", "sprint", "milestone", "roadmap",
        "vision", "system", "dispatcher", "runner", "infrastructure", "deploy",
    ],
    "user": [
        "eric", "adhd", "personality", "learning style", "preference", "behavior",
        "session pattern", "mood", "energy", "tunnel vision",
    ],
    "reference": [
        "tool", "resource", "external", "link", "source", "library", "framework",
        "vendor", "api", "sdk",
    ],
}

# Relative date patterns to absolutize
RELATIVE_DATE_PATTERNS = [
    r"\blast week\b",
    r"\blast month\b",
    r"\byesterday\b",
    r"\brecently\b",
    r"\bago\b",
    r"\bthis week\b",
    r"\btoday\b",
    r"\btomorrow\b",
    r"\bnext week\b",
    r"\bearlier this\b",
]


# --- Lock management ---

def _acquire_lock(dry_run: bool) -> bool:
    if dry_run:
        return True
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    if LOCK_FILE.exists():
        try:
            acquired_at = float(LOCK_FILE.read_text().strip())
            age = time.time() - acquired_at
            if age < LOCK_STALE_SECONDS:
                print(f"Dream run already in progress (lock age: {int(age)}s). Exiting.")
                return False
            print(f"Stale lock detected ({int(age)}s old) -- overriding.")
        except Exception:
            pass
    LOCK_FILE.write_text(str(time.time()))
    return True


def _release_lock(dry_run: bool) -> None:
    if not dry_run and LOCK_FILE.exists():
        LOCK_FILE.unlink()


# --- Snapshot ---

def _snapshot(fpath: Path) -> Path:
    SNAPSHOTS_DIR.mkdir(parents=True, exist_ok=True)
    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S")
    snap = SNAPSHOTS_DIR / f"{ts}_{fpath.name}"
    snap.write_text(fpath.read_text(encoding="utf-8", errors="replace"), encoding="utf-8")
    return snap


# --- Phase 1: Orient ---

def phase_orient() -> dict:
    """Inventory memory files and check state."""
    files = sorted(MEMORY_DIR.glob("*.md"))
    content_files = [f for f in files if f.name != "MEMORY.md"]

    last_run = "never"
    if LAST_RUN_FILE.exists():
        last_run = LAST_RUN_FILE.read_text().strip()

    return {
        "memory_files": content_files,
        "memory_index": MEMORY_INDEX,
        "file_count": len(content_files),
        "last_run": last_run,
        "protected_files": PROTECTED_FILES,
    }


# --- Phase 2: Gather Signal ---

def phase_gather(orientation: dict) -> dict:
    """Detect duplicates, stale pointers, and relative dates."""
    findings = {
        "duplicates": [],
        "related": [],
        "stale_pointers": [],
        "relative_date_files": [],
        "embedding_available": False,
    }

    # Attempt semantic duplicate scan
    try:
        sys.path.insert(0, str(REPO_ROOT / "tools" / "scripts"))
        import embedding_service as es
        result = es.find_similar(threshold=0.92)
        findings["duplicates"] = result.get("duplicates", [])
        findings["related"] = result.get("related", [])
        findings["embedding_available"] = True
    except Exception as e:
        findings["embedding_error"] = str(e)

    # Stale pointer check: parse MEMORY.md for (file.md) links
    if MEMORY_INDEX.exists():
        index_text = MEMORY_INDEX.read_text(encoding="utf-8", errors="replace")
        linked = re.findall(r'\(([^)]+\.md)\)', index_text)
        for link in linked:
            fpath = MEMORY_DIR / link
            if not fpath.exists():
                findings["stale_pointers"].append(link)

    # Relative date grep across all memory files
    rel_pattern = re.compile(
        "|".join(RELATIVE_DATE_PATTERNS), re.IGNORECASE
    )
    for fpath in orientation["memory_files"]:
        try:
            text = fpath.read_text(encoding="utf-8", errors="replace")
            # Skip frontmatter dates (---...---) and the word in URLs
            lines = text.split("\n")
            hits = [
                (i + 1, line.strip())
                for i, line in enumerate(lines)
                if rel_pattern.search(line)
                and not line.strip().startswith("http")
                and not line.strip().startswith("---")
            ]
            if hits:
                findings["relative_date_files"].append((fpath, hits))
        except Exception:
            pass

    return findings


# --- Phase 3: Consolidate ---

def _merge_files(keeper: Path, donor: Path, today_str: str) -> str:
    """Merge donor into keeper: append unique paragraphs from donor not in keeper.

    Returns a summary string describing what was merged.
    """
    keeper_text = keeper.read_text(encoding="utf-8", errors="replace")
    donor_text = donor.read_text(encoding="utf-8", errors="replace")

    # Split donor into paragraphs
    donor_paras = [p.strip() for p in donor_text.split("\n\n") if p.strip()]
    unique_paras = []
    for para in donor_paras:
        # Skip frontmatter, skip paragraphs already present in keeper
        if para.startswith("---"):
            continue
        # Simple containment check (first 60 chars as fingerprint)
        fingerprint = para[:60].lower()
        if fingerprint not in keeper_text.lower():
            unique_paras.append(para)

    merged = keeper_text
    if unique_paras:
        merged += (
            f"\n\n<!-- Merged from {donor.name} on {today_str} -->\n\n"
            + "\n\n".join(unique_paras)
        )

    keeper.write_text(merged, encoding="utf-8")
    return (
        f"Merged {len(unique_paras)} unique paragraph(s) from {donor.name} into {keeper.name}"
        if unique_paras else
        f"No unique content in {donor.name} -- deleted as exact duplicate"
    )


def _fix_relative_dates(fpath: Path, hits: list, today_str: str) -> int:
    """Replace flagged relative date lines with a note to use absolute dates.

    Conservative: annotates lines rather than guessing the absolute date,
    since guessing the wrong date is worse than flagging it.
    Returns count of lines annotated.
    """
    text = fpath.read_text(encoding="utf-8", errors="replace")
    lines = text.split("\n")
    count = 0
    rel_pattern = re.compile(
        "|".join(RELATIVE_DATE_PATTERNS), re.IGNORECASE
    )
    hit_line_nos = {h[0] for h in hits}
    for i, line in enumerate(lines):
        lineno = i + 1
        if lineno in hit_line_nos and rel_pattern.search(line):
            lines[i] = line + f"  <!-- TODO: absolutize date (dream run {today_str}) -->"
            count += 1
    if count:
        fpath.write_text("\n".join(lines), encoding="utf-8")
    return count


def _parse_frontmatter_field(fpath: Path, field: str) -> str | None:
    """Return the value of a YAML frontmatter field, or None if not found.

    Reads up to the first 30 lines of the file and looks for a --- block.
    Simple regex/string ops only -- no PyYAML dependency.
    """
    try:
        with fpath.open(encoding="utf-8", errors="replace") as fh:
            lines = [fh.readline() for _ in range(30)]
    except Exception:
        return None

    in_frontmatter = False
    field_pattern = re.compile(r"^" + re.escape(field) + r":\s*(.+)$")
    for line in lines:
        stripped = line.rstrip("\n")
        if stripped.strip() == "---":
            if not in_frontmatter:
                in_frontmatter = True
                continue
            else:
                break  # end of frontmatter block
        if in_frontmatter:
            m = field_pattern.match(stripped)
            if m:
                return m.group(1).strip()
    return None


def phase_consolidate(orientation: dict, findings: dict, dry_run: bool) -> list[str]:
    """Execute consolidation actions. Returns list of action strings for report."""
    actions = []
    today_str = datetime.now().strftime("%Y-%m-%d")

    # -- Merge duplicate pairs --
    merged_donors: set[str] = set()
    pruned_base = REPO_ROOT / "memory" / "learning" / "signals" / "pruned" / today_str

    for score, path_a, path_b in findings.get("duplicates", []):
        fa, fb = Path(path_a), Path(path_b)
        if not fa.exists() or not fb.exists():
            continue
        if str(fa) in merged_donors or str(fb) in merged_donors:
            continue

        # --- Protected file guard ---
        if is_protected(fa, REPO_ROOT) or is_protected(fb, REPO_ROOT):
            actions.append(
                f"[SKIP protected] {fa.name} or {fb.name}"
            )
            continue

        # --- Determine tier: is either file under MEMORY_DIR (auto-memory)? ---
        fa_is_auto = str(fa.resolve()).startswith(str(MEMORY_DIR.resolve()))
        fb_is_auto = str(fb.resolve()).startswith(str(MEMORY_DIR.resolve()))
        is_cross_tier = fa_is_auto != fb_is_auto  # exactly one side is auto-memory

        if not is_cross_tier:
            # --- Same-tier: existing behavior (keeper is larger, donor unlinked) ---
            keeper, donor = (fa, fb) if fa.stat().st_size >= fb.stat().st_size else (fb, fa)
            action = f"[MERGE score={score:.3f}] {keeper.name} absorbs {donor.name}"
            if dry_run:
                actions.append(f"[DRY-RUN] {action}")
            else:
                snap_keeper = _snapshot(keeper)
                snap_donor = _snapshot(donor)
                merge_summary = _merge_files(keeper, donor, today_str)
                donor.unlink()
                merged_donors.add(str(donor))
                actions.append(
                    f"{action}\n"
                    f"  {merge_summary}\n"
                    f"  Snapshots: {snap_keeper.name}, {snap_donor.name}"
                )
        else:
            # --- Cross-tier: auto-memory side is always keeper ---
            if fa_is_auto:
                keeper, donor = fa, fb
            else:
                keeper, donor = fb, fa

            # Provenance check: keeper.source frontmatter must match donor filename
            keeper_source = _parse_frontmatter_field(keeper, "source")
            if keeper_source != donor.name:
                actions.append(
                    f"[SKIP cross-tier no-provenance] {donor.name} "
                    f"(keeper.source={keeper_source!r})"
                )
                continue

            # Similarity floor assertion (already guaranteed by threshold=0.92, belt+suspenders)
            assert score >= 0.85, f"cross-tier pair below 0.85 floor: {score}"

            action = (
                f"[CROSS-TIER MERGE score={score:.3f}] {keeper.name} absorbs {donor.name} "
                f"(moved to pruned/{today_str}/)"
            )
            if dry_run:
                actions.append(f"[DRY-RUN] {action}")
            else:
                snap_keeper = _snapshot(keeper)
                snap_donor = _snapshot(donor)
                merge_summary = _merge_files(keeper, donor, today_str)
                pruned_base.mkdir(parents=True, exist_ok=True)
                shutil.move(str(donor), str(pruned_base / donor.name))
                merged_donors.add(str(donor))
                actions.append(
                    f"{action}\n"
                    f"  {merge_summary}\n"
                    f"  Snapshots: {snap_keeper.name}, {snap_donor.name}"
                )

    # -- Remove stale MEMORY.md pointers --
    for stale_link in findings.get("stale_pointers", []):
        action = f"[STALE PTR] Removed dead link: ({stale_link}) from MEMORY.md"
        if dry_run:
            actions.append(f"[DRY-RUN] {action}")
        else:
            if MEMORY_INDEX.exists():
                text = MEMORY_INDEX.read_text(encoding="utf-8", errors="replace")
                # Remove the entire line containing this stale link
                lines = text.split("\n")
                cleaned = [l for l in lines if f"({stale_link})" not in l]
                MEMORY_INDEX.write_text("\n".join(cleaned), encoding="utf-8")
            actions.append(action)

    # -- Flag relative dates --
    for fpath, hits in findings.get("relative_date_files", []):
        if not fpath.exists():
            continue
        action = f"[DATES] {fpath.name}: {len(hits)} relative date reference(s) flagged"
        if dry_run:
            actions.append(f"[DRY-RUN] {action}")
            for lineno, line in hits[:3]:
                actions.append(f"  line {lineno}: {line[:80]}")
        else:
            count = _fix_relative_dates(fpath, hits, today_str)
            actions.append(f"{action} (annotated {count} line(s))")

    return actions


# --- Phase 4: Prune & Index ---

def _infer_memory_type(theme_name: str, implication: str) -> str:
    """Infer auto-memory type from theme content. Defaults to 'feedback'."""
    combined = (theme_name + " " + implication).lower()
    for mem_type, keywords in TYPE_SIGNALS.items():
        if any(kw in combined for kw in keywords):
            return mem_type
    return "feedback"


def _slug_from_theme(theme_name: str) -> str:
    """Convert theme name to a filesystem-safe slug."""
    slug = re.sub(r"[^a-z0-9]+", "-", theme_name.lower()).strip("-")
    return slug[:60]


def _parse_synthesis_themes(fpath: Path) -> list[dict]:
    """Extract qualifying themes from a synthesis file.

    Returns list of dicts: {name, maturity, confidence, implication, source_file}
    Only returns themes meeting PROMOTION_MATURITY + PROMOTION_MIN_CONFIDENCE.
    """
    themes = []
    try:
        text = fpath.read_text(encoding="utf-8", errors="replace")
    except Exception:
        return themes

    # Split on ### Theme: headings
    blocks = re.split(r"^### Theme:", text, flags=re.MULTILINE)
    for block in blocks[1:]:  # skip header block before first theme
        lines = block.strip().split("\n")
        name = lines[0].strip()

        # Extract fields
        maturity = ""
        confidence_pct = 0
        implication = ""
        in_implication = False

        for line in lines[1:]:
            if line.startswith("- Maturity:"):
                maturity = line.split(":", 1)[1].strip().lower()
            elif line.startswith("- Confidence:"):
                conf_str = line.split(":", 1)[1].strip().rstrip("%")
                try:
                    confidence_pct = int(conf_str)
                except ValueError:
                    pass
            elif line.startswith("- Implication:"):
                implication = line.split(":", 1)[1].strip()
                in_implication = False  # single line
            elif line.startswith("- Action:"):
                in_implication = False

        # Apply promotion filter
        if maturity == PROMOTION_MATURITY and confidence_pct >= PROMOTION_MIN_CONFIDENCE:
            themes.append({
                "name": name,
                "maturity": maturity,
                "confidence": confidence_pct,
                "implication": implication,
                "source_file": str(fpath),
            })

    return themes


def phase_promote(dry_run: bool) -> list[str]:
    """Scan synthesis files for promotion candidates; write qualifying themes to auto-memory.

    A theme qualifies if:
    - maturity: proven AND confidence >= 90%
    - No semantic equivalent already exists in auto-memory (similarity < 0.70)

    Fully autonomous -- writes new auto-memory files, logs all actions.
    """
    actions = []
    today_str = datetime.now().strftime("%Y-%m-%d")

    if not SYNTHESIS_DIR.exists():
        return ["[PROMOTE] Synthesis dir not found -- skipping promotion scan"]

    # Collect all qualifying themes from all synthesis files
    all_themes = []
    for syn_file in sorted(SYNTHESIS_DIR.glob("*.md")):
        themes = _parse_synthesis_themes(syn_file)
        all_themes.extend(themes)

    if not all_themes:
        actions.append("[PROMOTE] No promotion candidates (no proven/90%+ themes in synthesis)")
        return actions

    # Load embedding service for similarity check
    try:
        sys.path.insert(0, str(REPO_ROOT / "tools" / "scripts"))
        import embedding_service as es
    except ImportError:
        actions.append("[PROMOTE] embedding_service unavailable -- skipping similarity check")
        return actions

    promoted = 0
    skipped_similar = 0

    auto_memory_prefix = str(MEMORY_DIR.resolve())

    for theme in all_themes:
        # Check if semantically covered in auto-memory already
        # Filter to auto-memory files only -- signals/synthesis/decisions should NOT block promotion
        try:
            hits = es.search(theme["implication"] or theme["name"], top_k=10)
            auto_hits = [h for h in hits if h["file_path"].startswith(auto_memory_prefix)]
            top_hit = auto_hits[0] if auto_hits else None
            top_score = top_hit["score"] if top_hit else 0.0
        except Exception:
            top_hit = None
            top_score = 0.0

        if top_score >= PROMOTION_MAX_SIMILARITY:
            skipped_similar += 1
            actions.append(
                f"[PROMOTE] SKIP '{theme['name'][:50]}' "
                f"(already covered: {top_hit['file_name']} @ {top_score:.2f})"
            )
            continue

        # Infer type and build slug
        mem_type = _infer_memory_type(theme["name"], theme["implication"])
        slug = _slug_from_theme(theme["name"])
        out_file = MEMORY_DIR / f"{mem_type}_{slug}.md"

        if out_file.exists():
            actions.append(f"[PROMOTE] SKIP '{theme['name'][:50]}' (file already exists: {out_file.name})")
            continue

        # Build the memory file content
        source_name = Path(theme["source_file"]).name
        content = (
            f"---\n"
            f"name: {theme['name']}\n"
            f"description: {theme['implication'][:120]}\n"
            f"type: {mem_type}\n"
            f"promoted: synthesis\n"
            f"promoted_date: {today_str}\n"
            f"source: {source_name}\n"
            f"confidence: {theme['confidence']}%\n"
            f"---\n\n"
            f"{theme['implication']}\n\n"
            f"**Why:** Promoted from synthesis theme '{theme['name']}' "
            f"({theme['confidence']}% confidence, maturity: {theme['maturity']}) "
            f"with no existing auto-memory counterpart (top similarity: {top_score:.2f}).\n\n"
            f"**How to apply:** This pattern emerged from accumulated signals -- "
            f"treat as validated behavioral guidance.\n"
        )

        action = (
            f"[PROMOTE] '{theme['name'][:50]}' -> {out_file.name} "
            f"(type={mem_type}, confidence={theme['confidence']}%, sim={top_score:.2f})"
        )

        if dry_run:
            actions.append(f"[DRY-RUN] {action}")
        else:
            out_file.write_text(content, encoding="utf-8")
            # Update embedding index for the new file
            try:
                es.update(str(out_file))
            except Exception:
                pass
            # Update MEMORY.md index
            _append_to_memory_index(out_file, theme["name"], theme["implication"])
            promoted += 1
            actions.append(action)

    if not dry_run:
        actions.append(f"[PROMOTE] Done: {promoted} promoted, {skipped_similar} skipped (already covered)")
    return actions


def _append_to_memory_index(fpath: Path, name: str, description: str) -> None:
    """Append a new entry to MEMORY.md for a promoted memory file."""
    if not MEMORY_INDEX.exists():
        return
    rel_name = fpath.name
    hook = description[:100].replace("\n", " ")
    entry = f"- [{name}]({rel_name}) -- {hook}\n"
    with open(MEMORY_INDEX, "a", encoding="utf-8") as f:
        f.write(entry)


def phase_prune_and_index(orientation: dict, consolidate_actions: list[str], dry_run: bool) -> list[str]:
    """Rebuild MEMORY.md index, update embeddings, write log + signal."""
    actions = []
    today_str = datetime.now().strftime("%Y-%m-%d")
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # Check MEMORY.md line count
    if MEMORY_INDEX.exists():
        lines = MEMORY_INDEX.read_text(encoding="utf-8", errors="replace").split("\n")
        line_count = len([l for l in lines if l.strip()])
        if line_count > MEMORY_INDEX_MAX_LINES:
            action = (
                f"[INDEX] MEMORY.md has {line_count} lines (limit: {MEMORY_INDEX_MAX_LINES}) "
                f"-- manual review needed to demote verbose entries"
            )
            actions.append(action)
        else:
            actions.append(f"[INDEX] MEMORY.md: {line_count} lines (within {MEMORY_INDEX_MAX_LINES} limit)")

    # Update embedding index for modified files
    if not dry_run:
        try:
            sys.path.insert(0, str(REPO_ROOT / "tools" / "scripts"))
            import embedding_service as es

            # Re-index any files that were modified during consolidation
            modified = [a for a in consolidate_actions if "[MERGE" in a or "[DATES" in a]
            if modified:
                es.index(scope="auto", verbose=False)
                actions.append(f"[INDEX] Embedding index updated ({len(modified)} file(s) changed)")
        except Exception as e:
            actions.append(f"[INDEX] Embedding update skipped: {e}")

    # Write dream log entry
    if not dry_run:
        DREAM_LOG.parent.mkdir(parents=True, exist_ok=True)
        log_entry = (
            f"\n## Dream Run: {now_str}\n\n"
            + "\n".join(f"- {a}" for a in consolidate_actions + actions)
            + "\n"
        )
        with open(DREAM_LOG, "a", encoding="utf-8") as f:
            f.write(log_entry)
        actions.append(f"[LOG] Appended to {DREAM_LOG.name}")

    # Write health signal
    if not dry_run:
        SIGNALS_DIR.mkdir(parents=True, exist_ok=True)
        merges = sum(1 for a in consolidate_actions if "[MERGE" in a and "[DRY" not in a)
        signal_file = SIGNALS_DIR / f"{today_str}_dream-health.md"
        signal_text = (
            f"---\n"
            f"date: {today_str}\n"
            f"category: dream\n"
            f"rating: 7\n"
            f"source: dream\n"
            f"---\n\n"
            f"# Dream health signal\n\n"
            f"Dream run completed at {now_str}.\n"
            f"- Files merged: {merges}\n"
            f"- Stale pointers removed: {len([a for a in consolidate_actions if '[STALE' in a])}\n"
            f"- Date flags added: {len([a for a in consolidate_actions if '[DATES' in a])}\n"
        )
        signal_file.write_text(signal_text, encoding="utf-8")
        actions.append(f"[SIGNAL] Health signal written: {signal_file.name}")

    # Update last-run timestamp
    if not dry_run:
        LAST_RUN_FILE.write_text(now_str)

    return actions


# --- Report ---

def _write_report(orientation: dict, findings: dict, consolidate_actions: list[str], promote_actions: list[str], prune_actions: list[str], dry_run: bool, duration_s: float) -> str:
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    mode = "DRY RUN" if dry_run else "COMPLETED"
    dupes_found = len(findings.get("duplicates", []))
    related_found = len(findings.get("related", []))
    promoted_count = sum(1 for a in promote_actions if "[PROMOTE]" in a and "SKIP" not in a and "Done" not in a and "unavailable" not in a and "not found" not in a and "No promotion" not in a and "DRY" not in a)

    lines = [
        f"# /dream Report -- {now_str} ({mode})",
        f"",
        f"## Summary",
        f"- Files scanned: {orientation['file_count']}",
        f"- Last run: {orientation['last_run']}",
        f"- Duration: {duration_s:.1f}s",
        f"- Semantic engine: {'OK (nomic-embed-text)' if findings.get('embedding_available') else 'UNAVAILABLE (grep fallback)'}",
        f"",
        f"## Findings",
        f"- Duplicate candidates (>= 0.92): {dupes_found}",
        f"- Related pairs (0.82-0.91): {related_found} (no action)",
        f"- Stale MEMORY.md pointers: {len(findings.get('stale_pointers', []))}",
        f"- Files with relative dates: {len(findings.get('relative_date_files', []))}",
        f"- Synthesis themes promoted: {promoted_count}",
        f"",
        f"## Actions Taken",
    ]

    all_actions = consolidate_actions + promote_actions + prune_actions
    if not any(a for a in all_actions if "[DRY" not in a or dry_run):
        lines.append("- No changes needed -- memory is clean")
    else:
        for a in all_actions:
            for subline in a.split("\n"):
                lines.append(f"- {subline}" if not subline.startswith("  ") else subline)

    if findings.get("related"):
        lines += ["", "## Related Pairs (informational)"]
        for score, a, b in findings["related"][:10]:
            lines.append(f"- {score:.3f}  {Path(a).name}  <->  {Path(b).name}")

    if dry_run:
        lines += ["", "---", "*Dry run -- no files were modified.*"]

    if SNAPSHOTS_DIR.exists():
        snaps = list(SNAPSHOTS_DIR.glob("*.md"))
        if snaps:
            lines += ["", f"## Snapshots Available ({len(snaps)} files)"]
            lines.append(f"- Location: {SNAPSHOTS_DIR}")
            lines.append("- Revert: copy snapshot file back over original, or use git")

    report = "\n".join(lines) + "\n"

    if not dry_run:
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        REPORT_FILE.write_text(report, encoding="utf-8")

    return report


# --- Main ---

def run(dry_run: bool = False, autonomous: bool = False) -> int:
    t0 = time.time()

    if not _acquire_lock(dry_run):
        return 1

    try:
        # Phase 1
        orientation = phase_orient()
        if not autonomous:
            print(f"Phase 1: Orient -- {orientation['file_count']} memory files, "
                  f"last run: {orientation['last_run']}")

        # Phase 2
        findings = phase_gather(orientation)
        if not autonomous:
            dupes = len(findings.get("duplicates", []))
            stale = len(findings.get("stale_pointers", []))
            dates = len(findings.get("relative_date_files", []))
            print(f"Phase 2: Gather  -- {dupes} duplicates, {stale} stale ptrs, "
                  f"{dates} relative-date files")

        # Phase 3
        consolidate_actions = phase_consolidate(orientation, findings, dry_run)
        if not autonomous:
            print(f"Phase 3: Consolidate -- {len(consolidate_actions)} action(s)")

        # Phase 3B: Promotion scan (synthesis -> auto-memory)
        promote_actions = phase_promote(dry_run)
        if not autonomous:
            promoted = sum(1 for a in promote_actions if "[PROMOTE]" in a and "SKIP" not in a and "DRY" not in a and "Done" not in a and "unavailable" not in a and "not found" not in a and "No promotion" not in a)
            print(f"Phase 3B: Promote  -- {promoted} theme(s) promoted from synthesis")

        # Phase 4
        all_consolidate = consolidate_actions + promote_actions
        prune_actions = phase_prune_and_index(orientation, all_consolidate, dry_run)
        if not autonomous:
            print(f"Phase 4: Prune+Index -- {len(prune_actions)} action(s)")

        duration = round(time.time() - t0, 1)
        report = _write_report(
            orientation, findings, consolidate_actions, promote_actions, prune_actions, dry_run, duration
        )

        print("\n" + report)
        if not dry_run:
            print(f"Full report saved: {REPORT_FILE}")

        return 0

    except Exception as e:
        _release_lock(dry_run)
        # Write failure signal
        try:
            SIGNALS_DIR.mkdir(parents=True, exist_ok=True)
            today = datetime.now().strftime("%Y-%m-%d")
            fail_signal = SIGNALS_DIR / f"{today}_dream-failure.md"
            fail_signal.write_text(
                f"---\ndate: {today}\ncategory: dream\nrating: 9\nsource: dream\n---\n\n"
                f"# Dream FAILURE\n\nUnhandled exception: {e}\n",
                encoding="utf-8",
            )
            DREAM_LOG.parent.mkdir(parents=True, exist_ok=True)
            with open(DREAM_LOG, "a", encoding="utf-8") as f:
                f.write(f"\n## Dream FAILURE: {datetime.now()}\n\n- Exception: {e}\n")
        except Exception:
            pass
        raise

    finally:
        _release_lock(dry_run)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Jarvis /dream -- memory consolidation"
    )
    parser.add_argument(
        "--dry-run", action="store_true",
        help="Show what would change without making any writes"
    )
    parser.add_argument(
        "--autonomous", action="store_true",
        help="Overnight mode: suppress progress output, write report only"
    )
    args = parser.parse_args()
    sys.exit(run(dry_run=args.dry_run, autonomous=args.autonomous))


if __name__ == "__main__":
    main()
