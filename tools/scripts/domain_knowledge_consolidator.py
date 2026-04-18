#!/usr/bin/env python3
"""Domain Knowledge Consolidator -- weekly synthesis of knowledge articles.

Reads raw knowledge articles from multiple producers, applies first-principles
and fallacy-detection lenses via Claude Sonnet, writes _context.md (domain
summary) and sub-domain files. Runs in a git worktree; output is proposal-only
until Eric runs --commit.

Usage:
    python tools/scripts/domain_knowledge_consolidator.py --dry-run
    python tools/scripts/domain_knowledge_consolidator.py --autonomous
    python tools/scripts/domain_knowledge_consolidator.py --commit
    python tools/scripts/domain_knowledge_consolidator.py --reject crypto
    python tools/scripts/domain_knowledge_consolidator.py --reject-all
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

# ---------------------------------------------------------------------------
# Repo layout
# ---------------------------------------------------------------------------
REPO_ROOT = Path(__file__).resolve().parents[2]
KNOWLEDGE_DIR = REPO_ROOT / "memory" / "knowledge"
ABSORBED_DIR = REPO_ROOT / "memory" / "learning" / "absorbed"
MORNING_FEED_DIR = REPO_ROOT / "memory" / "work" / "jarvis" / "morning_feed"
PREDICTIONS_DIR = REPO_ROOT / "data" / "predictions"
SYNTHESIS_DIR = REPO_ROOT / "memory" / "learning" / "synthesis"
STATE_FILE = REPO_ROOT / "data" / "domain_consolidator_state.json"
SIGNALS_DIR = REPO_ROOT / "memory" / "learning" / "signals"

WORKTREE_DIR = REPO_ROOT.parent / "epdev-knowledge-worktree"

_CONTEXT_CHAR_CAP = 8000
_SUBDOMAIN_CHAR_CAP = 6000

# Domains where prediction/backtest files are valid source inputs
_PREDICTION_DOMAINS = {"fintech", "geopolitics", "predictions"}

# Keyword sets for matching absorbed articles to domains
_DOMAIN_KEYWORDS: dict[str, list[str]] = {
    "ai-infra": ["agent", "orchestration", "harness", "embedding", "claude", "llm",
                 "autonomous", "coding", "ai infrastructure", "machine learning",
                 "prediction framework", "calibration", "brier"],
    "fintech": ["banking", "finance", "consulting", "osfi", "fintech", "ai adoption",
                "bank", "credit", "lending", "payment", "regtech"],
    "crypto": ["crypto", "defi", "mev", "freqtrade", "bitcoin", "ethereum",
               "blockchain", "trading bot", "dex", "nft", "solana"],
    "security": ["security", "injection", "prompt injection", "mcp", "attack",
                 "vulnerability", "threat", "defense", "exploit", "agentic security"],
    "geopolitics": ["geopolitics", "iran", "russia", "ukraine", "nato", "geopolitical",
                    "foreign policy", "nuclear", "sanctions", "war", "election",
                    "middle east", "china", "taiwan"],
    "predictions": ["prediction", "forecasting", "calibration", "brier", "backtest",
                    "base rate", "superforecasting", "metaculus", "polymarket"],
    "automotive": ["byd", "ev", "electric vehicle", "car", "ioniq", "automotive"],
    "smart-home": ["smart home", "home assistant", "iot", "alexa", "google home"],
    "music": ["guitar", "music", "band", "jazz", "grateful dead", "chord", "improvisation",
              "song", "performance", "instrument"],
    "health-fitness": ["gym", "workout", "cardio", "weightlifting", "nutrition",
                       "health tracker", "body composition", "macros", "protein intake"],
    "financial-independence": ["revenue", "substack", "freelance", "side hustle", "passive income",
                               "business income", "consulting income", "content creator"],
    "general": [],
}

# TELOS goal references per domain — drives reason string attribution
_DOMAIN_TELOS_REFS: dict[str, str] = {
    "ai-infra": "G2 (Master AI systems)",
    "crypto": "G1 (Financial independence — crypto-bot)",
    "fintech": "G1 (Financial independence — fintech knowledge)",
    "geopolitics": "G2 (Master AI systems — geopolitical forecasting)",
    "predictions": "G2 (Master AI systems — calibration framework)",
    "music": "G3 (Guitar mastery)",
    "health-fitness": "G4 (Physical health)",
    "financial-independence": "G1 (Financial independence)",
}

# CLAUDE.md routing trigger keywords per domain (for Phase 4 update)
_CLAUDE_MD_KEYWORDS: dict[str, str] = {
    "ai-infra": "agent, orchestration, harness, embedding, LLM, autonomous coding, Claude API, agentic",
    "fintech": "banking, finance, OSFI, fintech, AI adoption, consulting, bank AI",
    "crypto": "crypto, DeFi, MEV, Freqtrade, bitcoin, ethereum, trading bot",
    "security": "security, injection, prompt injection, MCP threat, agentic attack, vulnerability",
    "geopolitics": "geopolitics, Iran, Russia, Ukraine, NATO, geopolitical, foreign policy, election",
}


# ---------------------------------------------------------------------------
# State management
# ---------------------------------------------------------------------------
def _load_state() -> dict:
    """Load state from disk. Returns empty dict if absent or corrupt."""
    if not STATE_FILE.exists():
        return {}
    try:
        data = json.loads(STATE_FILE.read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else {}
    except (json.JSONDecodeError, OSError):
        return {}


def _save_state(state: dict) -> None:
    """Persist state using locked read-modify-write."""
    sys.path.insert(0, str(REPO_ROOT))
    from tools.scripts.lib.file_lock import locked_read_modify_write  # noqa: E402
    STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    locked_read_modify_write(STATE_FILE, lambda _: state, default={})


# ---------------------------------------------------------------------------
# Source reading
# ---------------------------------------------------------------------------
def _read_raw_articles(domain: str) -> list[dict]:
    """Read all YYYY-MM-DD_*.md files from a domain directory."""
    domain_dir = KNOWLEDGE_DIR / domain
    if not domain_dir.exists():
        return []
    files = sorted(domain_dir.glob("2[0-9]*_*.md"))
    results = []
    for f in files:
        try:
            content = f.read_text(encoding="utf-8", errors="replace")
            results.append({"path": str(f.relative_to(REPO_ROOT)), "content": content,
                            "filename": f.name, "source_type": "raw_article"})
        except OSError:
            pass
    return results


def _read_absorbed_articles(domain: str) -> list[dict]:
    """Read absorbed articles keyword-matched to the domain."""
    if not ABSORBED_DIR.exists():
        return []
    keywords = _DOMAIN_KEYWORDS.get(domain, [])
    if not keywords:
        return []
    results = []
    for f in sorted(ABSORBED_DIR.glob("2[0-9]*_*.md")):
        try:
            content = f.read_text(encoding="utf-8", errors="replace")
            lower = content.lower()
            if any(kw.lower() in lower for kw in keywords):
                results.append({"path": str(f.relative_to(REPO_ROOT)), "content": content,
                                "filename": f.name, "source_type": "absorbed"})
        except OSError:
            pass
    return results


def _read_morning_feed(domain: str) -> list[dict]:
    """Read B+ rated items from last 30d morning feed files.

    Morning feed format does not have per-item B+/C/D ratings in a parseable
    structure; this is a stub that skips with a logged reason until the format
    is confirmed stable (R2 risk in PRD).
    """
    # Morning feed briefings are summaries, not structured per-item rating files.
    # Stub: return empty list with a skip note.
    return []


def _read_predictions(domain: str) -> list[dict]:
    """Read prediction and backtest files for eligible domains."""
    if domain not in _PREDICTION_DOMAINS:
        return []
    if not PREDICTIONS_DIR.exists():
        return []

    # Map domain to file prefixes
    prefix_map = {
        "geopolitics": ["geo-", "geo_"],
        "predictions": [],  # all predictions
        "fintech": ["mkt-", "mkt_"],
    }
    prefixes = prefix_map.get(domain, [])

    results = []
    for subdir in [PREDICTIONS_DIR, PREDICTIONS_DIR / "backtest"]:
        if not subdir.exists():
            continue
        for f in sorted(subdir.glob("*.md")):
            if prefixes and not any(f.name.startswith(p) for p in prefixes):
                continue
            try:
                content = f.read_text(encoding="utf-8", errors="replace")
                results.append({"path": str(f.relative_to(REPO_ROOT)), "content": content,
                                "filename": f.name, "source_type": "prediction"})
            except OSError:
                pass
    return results


def _read_synthesis_themes(domain: str) -> list[dict]:
    """Read domain-tagged themes from synthesis docs.

    Synthesis docs are Jarvis dev pattern signals, not external domain knowledge.
    Stub: return empty -- cross-contamination risk is too high without explicit
    domain tags in synthesis YAML frontmatter (not yet present).
    """
    return []


def _gather_sources(domain: str, state: dict, dry_run: bool = False) -> tuple[list[dict], list[str]]:
    """Gather all source files for a domain, applying incremental filter.

    Returns (new_sources, already_incorporated_paths).
    """
    domain_state = state.get(domain, {})
    incorporated = set(domain_state.get("incorporated_files", []))

    raw = _read_raw_articles(domain)
    absorbed = _read_absorbed_articles(domain)
    predictions = _read_predictions(domain)
    morning = _read_morning_feed(domain)
    synthesis = _read_synthesis_themes(domain)

    all_sources = raw + absorbed + predictions + morning + synthesis

    # Incremental: only new files since last consolidation
    new_sources = [s for s in all_sources if s["path"] not in incorporated]

    # Cap total sources per domain to prevent LLM timeout on large domains
    if len(new_sources) > _MAX_SOURCES_PER_DOMAIN:
        new_sources = new_sources[:_MAX_SOURCES_PER_DOMAIN]

    if dry_run:
        print(f"  {domain}: {len(all_sources)} total sources, {len(new_sources)} new "
              f"({len(raw)} raw, {len(absorbed)} absorbed, {len(predictions)} predictions)")

    return new_sources, list(incorporated)


# ---------------------------------------------------------------------------
# LLM synthesis
# ---------------------------------------------------------------------------
_SYSTEM_PROMPT = """You are a knowledge synthesizer for an AI personal assistant system called Jarvis.
Your task: synthesize research articles into structured domain knowledge files.
Output format: valid JSON only, no markdown code fences, no prose outside JSON.
Apply rigorously:
- First-principles lens: identify unstated assumptions in each article
- Fallacy-detection lens: check for hasty generalization, survivorship bias, false dichotomy, appeal to authority
All output must be ASCII-safe (no Unicode curly quotes, no em-dashes, use plain ASCII equivalents)."""


_MAX_ARTICLES_PER_BATCH = 6
_ARTICLE_CONTENT_LIMIT = 800
_MAX_SOURCES_PER_DOMAIN = 20  # Cap total sources fed to LLM per run


def _build_synthesis_prompt(domain: str, sources: list[dict], existing_context: str = "") -> str:
    """Build the LLM synthesis prompt for a domain."""
    parts = []
    parts.append(f"Domain: {domain}")
    parts.append(f"Source articles: {len(sources)}")
    if existing_context:
        parts.append(f"\nExisting _context.md (for incremental update):\n{existing_context[:1500]}")
    parts.append("\n--- SOURCE ARTICLES ---")
    for i, src in enumerate(sources, 1):
        # Truncate individual articles to keep prompt manageable
        content = src["content"][:_ARTICLE_CONTENT_LIMIT]
        parts.append(f"\n[Article {i}: {src['filename']} ({src['source_type']})]\n{content}")

    parts.append(f"""
--- SYNTHESIS TASK ---

1. CLUSTER: Group these {len(sources)} articles into 2-4 DISTINCT sub-topics using different names.
   Use slug names that reflect the actual sub-topic (e.g., "agent-orchestration",
   "context-engineering", "harness-tooling", "prediction-calibration").
   - A sub-domain requires >= 2 articles. Single articles go into _context.md directly.
   - Use DIFFERENT sub-domain names for each cluster -- do NOT merge all into one.

2. For each sub-domain cluster: write a sub-domain file with a unique descriptive name.
3. Write a domain _context.md summary (all clusters summarized).

Return ONLY this JSON structure (no prose, no markdown fences):
{{
  "context_md": "<_context.md content, ASCII-safe, under {_CONTEXT_CHAR_CAP} chars>",
  "subdomains": [
    {{
      "name": "<unique-slug-distinct-from-other-clusters>",
      "title": "<Human Readable Title>",
      "article_count": <int>,
      "content": "<sub-domain file content, ASCII-safe, under {_SUBDOMAIN_CHAR_CAP} chars>"
    }}
  ],
  "caveats_per_subdomain": {{
    "<slug>": ["<assumption 1>", "<fallacy detected 1>"]
  }},
  "contradictions": ["<contradiction between articles>"],
  "summary_stats": {{
    "articles_processed": {len(sources)},
    "subdomains_created": <int matching len(subdomains)>
  }}
}}

REQUIREMENTS:
- context_md: Start with "# {domain.title()} Domain Knowledge\\n\\n". Include: domain overview,
  key findings per sub-domain (2-3 bullets each), cross-cutting themes.
  Hard cap: {_CONTEXT_CHAR_CAP} characters. Summarize aggressively if needed.
- sub-domain files: Start with "# <Title>\\n\\n". Include: overview, key findings (bulleted),
  source articles list, ## Caveats section.
  Hard cap: {_SUBDOMAIN_CHAR_CAP} characters.
- Caveats section format:
  ## Caveats
  > LLM-flagged, unverified. Review during weekly consolidation.
  - [ASSUMPTION] <unstated assumption found in source articles>
  - [FALLACY] <logical fallacy detected>
- All strings: ASCII only. Replace curly quotes with straight quotes. Replace em-dash with --.
- IMPORTANT: Each batch must produce sub-domains with UNIQUE names not already used by other batches.
  Prefix with topic area if needed: "{domain}-<subtopic>" pattern.
""")
    return "\n".join(parts)


def _call_llm(prompt: str, model: str = "claude-sonnet-4-6") -> dict | None:
    """Call Claude Sonnet via claude -p subprocess (stdin). Returns parsed JSON or None.

    Uses claude CLI auth (no ANTHROPIC_API_KEY env var required).
    Passes prompt via stdin (not CLI arg) to avoid Windows command-line length limits.
    """
    import re as _re
    full_prompt = f"{_SYSTEM_PROMPT}\n\n{prompt}"
    try:
        result = subprocess.run(
            ["claude", "-p", "--model", model],
            input=full_prompt,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=240,
            cwd=str(REPO_ROOT),
        )
        if result.returncode == 0 and result.stdout.strip():
            text = result.stdout.strip()
            # Strip accidental code fences
            if text.startswith("```"):
                lines = text.splitlines()
                text = "\n".join(lines[1:-1] if lines[-1].strip() == "```" else lines[1:])
            try:
                return json.loads(text)
            except json.JSONDecodeError:
                # Try extracting JSON block from prose response
                match = _re.search(r"\{[\s\S]+\}", text)
                if match:
                    try:
                        return json.loads(match.group(0))
                    except json.JSONDecodeError:
                        pass
                print(f"  LLM JSON parse error. Response (first 300 chars): {text[:300]}",
                      file=sys.stderr)
                return None
        else:
            stderr_snippet = (result.stderr or "")[:300]
            stdout_snippet = (result.stdout or "")[:200]
            print(f"  claude -p failed (exit {result.returncode}): {stderr_snippet or stdout_snippet}",
                  file=sys.stderr)
            return None
    except subprocess.TimeoutExpired:
        print("  claude -p timed out after 120s", file=sys.stderr)
        return None
    except FileNotFoundError:
        print("  claude CLI not found in PATH", file=sys.stderr)
        return None
    except OSError as exc:
        print(f"  claude -p OS error: {exc}", file=sys.stderr)
        return None


# ---------------------------------------------------------------------------
# Batched synthesis for large domains
# ---------------------------------------------------------------------------
def _synthesize_batched(domain: str, sources: list[dict], existing_context: str = "") -> dict | None:
    """Synthesize a large domain in batches, merging results.

    For domains with > _MAX_ARTICLES_PER_BATCH sources: run multiple passes,
    then a final merge pass to produce the unified _context.md + sub-domains.
    """
    import math
    batch_size = _MAX_ARTICLES_PER_BATCH
    n_batches = math.ceil(len(sources) / batch_size)
    print(f"  Large domain ({len(sources)} sources) -- processing in {n_batches} batches")

    batch_results = []
    for i in range(n_batches):
        batch = sources[i * batch_size: (i + 1) * batch_size]
        print(f"  Batch {i + 1}/{n_batches} ({len(batch)} articles)...")
        prompt = _build_synthesis_prompt(domain, batch, existing_context if i == 0 else "")
        res = _call_llm(prompt)
        if res:
            batch_results.append(res)
        else:
            print(f"  Batch {i + 1} failed -- continuing", file=sys.stderr)

    if not batch_results:
        return None

    # Merge batch results
    merged_subdomains: dict[str, dict] = {}
    merged_contradictions: list[str] = []
    merged_caveats: dict[str, list[str]] = {}
    articles_total = 0

    for br in batch_results:
        articles_total += br.get("summary_stats", {}).get("articles_processed", 0)
        for sd in br.get("subdomains", []):
            name = sd.get("name", "")
            if name not in merged_subdomains:
                merged_subdomains[name] = sd
            else:
                # Merge content (concatenate key findings)
                existing = merged_subdomains[name]
                existing["content"] = existing["content"] + "\n\n" + sd.get("content", "")
                existing["article_count"] = (existing.get("article_count", 0)
                                             + sd.get("article_count", 0))
        merged_contradictions.extend(br.get("contradictions", []))
        for slug, cavs in br.get("caveats_per_subdomain", {}).items():
            merged_caveats.setdefault(slug, []).extend(cavs)

    # Build merged context_md from all batch context_mds
    context_parts = [f"# {domain.title()} Domain Knowledge\n"]
    for br in batch_results:
        ctx = br.get("context_md", "")
        if ctx:
            # Skip repeated headers
            lines = ctx.splitlines()
            body = "\n".join(ln for ln in lines if not ln.startswith("# "))
            context_parts.append(body)
    merged_context = "\n\n".join(context_parts)

    return {
        "context_md": merged_context,
        "subdomains": list(merged_subdomains.values()),
        "caveats_per_subdomain": merged_caveats,
        "contradictions": list(set(merged_contradictions)),
        "summary_stats": {
            "articles_processed": articles_total,
            "subdomains_created": len(merged_subdomains),
        },
    }


# ---------------------------------------------------------------------------
# Output writing
# ---------------------------------------------------------------------------
def _enforce_cap(content: str, cap: int, label: str) -> str:
    """Truncate content to cap characters, appending a truncation notice."""
    if len(content) <= cap:
        return content
    truncation_note = f"\n\n[TRUNCATED: content exceeded {cap} char cap -- {label}]"
    return content[: cap - len(truncation_note)] + truncation_note


def _write_context_md(domain_dir: Path, content: str, dry_run: bool) -> int:
    """Write _context.md to domain_dir. Returns bytes written."""
    content = _enforce_cap(content, _CONTEXT_CHAR_CAP, "_context.md")
    if not dry_run:
        domain_dir.mkdir(parents=True, exist_ok=True)
        (domain_dir / "_context.md").write_text(content, encoding="utf-8")
    return len(content)


def _write_subdomain_file(domain_dir: Path, name: str, content: str, caveats: list[str],
                          dry_run: bool) -> int:
    """Write a sub-domain file, injecting caveats section. Returns bytes written."""
    # Inject caveats if not already present
    if "## Caveats" not in content and caveats:
        caveats_block = "\n\n## Caveats\n> LLM-flagged, unverified. Review during weekly consolidation.\n"
        for c in caveats:
            caveats_block += f"- {c}\n"
        content = content + caveats_block
    content = _enforce_cap(content, _SUBDOMAIN_CHAR_CAP, f"{name}.md")
    if not dry_run:
        domain_dir.mkdir(parents=True, exist_ok=True)
        (domain_dir / f"{name}.md").write_text(content, encoding="utf-8")
    return len(content)


# ---------------------------------------------------------------------------
# Domain lifecycle
# ---------------------------------------------------------------------------
def _detect_domains(state: dict) -> list[str]:
    """Return all existing domain directories under memory/knowledge/."""
    if not KNOWLEDGE_DIR.exists():
        return []
    return [d.name for d in KNOWLEDGE_DIR.iterdir()
            if d.is_dir() and not d.name.startswith(".")]


def _read_synthesis_theme_hints() -> list[str]:
    """Return theme names from the 3 most recent synthesis files."""
    import re as _re
    if not SYNTHESIS_DIR.exists():
        return []
    themes = []
    for f in sorted(SYNTHESIS_DIR.glob("*_synthesis.md"))[-3:]:
        try:
            content = f.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        for m in _re.finditer(r"### Theme \d+: (.+)", content):
            themes.append(m.group(1).strip())
    return themes


def _propose_new_domains(existing_domains: list[str]) -> list[dict]:
    """Propose new domains from _DOMAIN_KEYWORDS entries not yet created.

    Evidence sources (in reason string):
    - Absorbed article count matching domain keywords
    - TELOS goal reference from _DOMAIN_TELOS_REFS
    - Synthesis theme name if theme text overlaps domain keywords
    """
    if not ABSORBED_DIR.exists():
        return []

    synthesis_themes = _read_synthesis_theme_hints()
    proposals = []

    for domain, keywords in _DOMAIN_KEYWORDS.items():
        if domain in existing_domains or domain == "general" or not keywords:
            continue

        # Count absorbed articles matching domain keywords
        matched_files: list[str] = []
        for f in sorted(ABSORBED_DIR.glob("2[0-9]*_*.md")):
            try:
                content = f.read_text(encoding="utf-8", errors="replace").lower()
            except OSError:
                continue
            if any(kw.lower() in content for kw in keywords):
                matched_files.append(f.name)

        if not matched_files:
            continue

        # Build reason string: articles + TELOS ref + synthesis theme if relevant
        reason_parts = [f"{len(matched_files)} absorbed article(s) matching '{', '.join(keywords[:3])}'"]

        telos_ref = _DOMAIN_TELOS_REFS.get(domain)
        if telos_ref:
            reason_parts.append(f"TELOS {telos_ref}")

        relevant_themes = [t for t in synthesis_themes
                           if any(kw.lower() in t.lower() for kw in keywords[:4])]
        if relevant_themes:
            reason_parts.append(f"synthesis theme: '{relevant_themes[0]}'")

        proposals.append({
            "domain": domain,
            "reason": " — ".join(reason_parts),
            "source_files": matched_files[:5],
        })

    return proposals


def _check_retirement_candidates(domains: list[str], state: dict) -> list[dict]:
    """Return domains that meet retirement criteria."""
    candidates = []
    now = datetime.now(timezone.utc)
    ninety_days_ago = now - timedelta(days=90)

    for domain in domains:
        domain_dir = KNOWLEDGE_DIR / domain
        articles = list(domain_dir.glob("2[0-9]*_*.md")) if domain_dir.exists() else []
        if not articles:
            continue
        if len(articles) <= 1:
            # Check age of most recent article
            newest = max(articles, key=lambda f: f.stat().st_mtime)
            mtime = datetime.fromtimestamp(newest.stat().st_mtime, tz=timezone.utc)
            if mtime < ninety_days_ago:
                candidates.append({
                    "domain": domain,
                    "article_count": len(articles),
                    "last_article": newest.name,
                    "days_old": (now - mtime).days,
                    "reason": f"<= 1 article, last updated {(now - mtime).days} days ago",
                })
            elif domain == "general":
                # Flag general for retirement on first run regardless
                candidates.append({
                    "domain": domain,
                    "article_count": len(articles),
                    "last_article": newest.name,
                    "days_old": (now - mtime).days,
                    "reason": "general domain -- flag for retirement, redistribute articles",
                })
        elif domain == "general":
            candidates.append({
                "domain": domain,
                "article_count": len(articles),
                "last_article": articles[-1].name if articles else "none",
                "days_old": 0,
                "reason": "general domain -- all articles should be reassigned to specific domains",
            })

    return candidates


# ---------------------------------------------------------------------------
# Report writing
# ---------------------------------------------------------------------------
def _write_consolidation_report(
    output_dir: Path,
    domain_results: list[dict],
    new_domain_proposals: list[dict],
    retirement_candidates: list[dict],
    dry_run: bool,
) -> str:
    """Write _consolidation_report.md. Returns report path string."""
    now_str = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    lines = [
        "# Domain Knowledge Consolidation Report",
        f"> Generated: {now_str}",
        "",
    ]

    # Summary
    total_processed = sum(r.get("articles_processed", 0) for r in domain_results)
    total_subdomains = sum(len(r.get("subdomains", [])) for r in domain_results)
    total_contradictions = sum(len(r.get("contradictions", [])) for r in domain_results)
    total_taxonomy_changes = len(new_domain_proposals) + len(retirement_candidates)

    lines += [
        "## Summary",
        f"- Domains processed: {len(domain_results)}",
        f"- Article count (new): {total_processed}",
        f"- Sub-domains proposed: {total_subdomains}",
        f"- Taxonomy changes proposed: {total_taxonomy_changes}",
        f"- Contradictions detected: {total_contradictions}",
        "",
    ]

    # Per-domain results
    lines.append("## Domain Results")
    for r in domain_results:
        domain = r["domain"]
        lines.append(f"\n### {domain}")
        lines.append(f"- Article count (new this run): {r.get('articles_processed', 0)}")
        lines.append(f"- _context.md: {r.get('context_chars', 0)} chars")
        subdomains = r.get("subdomains", [])
        if subdomains:
            lines.append(f"- Proposed sub-domains ({len(subdomains)}): "
                         + ", ".join(f"`{s['name']}.md`" for s in subdomains))
        contradictions = r.get("contradictions", [])
        if contradictions:
            lines.append("- Contradictions:")
            for c in contradictions:
                lines.append(f"  - {c}")

    # New domain proposals
    if new_domain_proposals:
        lines += ["", "## Proposed New Domains"]
        for p in new_domain_proposals:
            lines.append(f"\n### {p['domain']}")
            lines.append(f"- Reason: {p['reason']}")
            if p.get("source_files"):
                lines.append(f"- Source files: {', '.join(p['source_files'][:5])}")
            lines.append("- Action required: Eric approval before domain dir is created")

    # Retirement candidates
    if retirement_candidates:
        lines += ["", "## Proposed Domain Retirements"]
        for c in retirement_candidates:
            lines.append(f"\n### {c['domain']} -- retire")
            lines.append(f"- Article count: {c['article_count']}")
            lines.append(f"- Last article: {c['last_article']} ({c['days_old']} days old)")
            lines.append(f"- Reason: {c['reason']}")
            if c["domain"] == "general":
                lines.append("- Action: Remove CLAUDE.md routing entry; add RETIRED notice to index.md")
                lines.append("- general domain articles need reassignment:")
                general_dir = KNOWLEDGE_DIR / "general"
                if general_dir.exists():
                    for f in sorted(general_dir.glob("2[0-9]*_*.md")):
                        lines.append(f"  - {f.name} -> (assign to domain)")

    lines.append("")
    report_content = "\n".join(lines)

    report_path = output_dir / "_consolidation_report.md"
    if not dry_run:
        output_dir.mkdir(parents=True, exist_ok=True)
        report_path.write_text(report_content, encoding="utf-8")

    return str(report_path)


# ---------------------------------------------------------------------------
# Index update
# ---------------------------------------------------------------------------
def _update_index_md(output_dir: Path, new_domain_proposals: list[dict],
                     domain_results: list[dict], dry_run: bool) -> None:
    """Update memory/knowledge/index.md with new domains and sub-domain paths."""
    index_src = KNOWLEDGE_DIR / "index.md"
    index_dst = output_dir / "memory" / "knowledge" / "index.md"

    if not index_src.exists():
        return

    content = index_src.read_text(encoding="utf-8")

    # Add sub-domain references for domains that now have sub-domain files
    for r in domain_results:
        domain = r["domain"]
        subdomains = r.get("subdomains", [])
        domain_section_marker = f"## {domain}\n"
        if subdomains and domain_section_marker in content:
            subdomain_line = "Sub-domains: " + ", ".join(
                f"`{domain}/{s['name']}.md`" for s in subdomains
            )
            # Insert after domain header if not already present
            if "Sub-domains:" not in content[content.find(domain_section_marker):
                                              content.find(domain_section_marker) + 200]:
                content = content.replace(
                    domain_section_marker,
                    f"{domain_section_marker}{subdomain_line}\n\n",
                )

    # Add new domain sections for proposed new domains (from proposals)
    for p in new_domain_proposals:
        domain = p["domain"]
        if f"## {domain}" not in content:
            content += f"\n## {domain}\n\n"
            content += "| Date | Topic | Key Finding | Path |\n"
            content += "|------|-------|-------------|------|\n"
            content += f"| (proposed) | (new domain -- first run) | {p['reason']} | `{domain}/` |\n"

    # Also add entries for any synthesized domains not in index yet
    # (handles case where domain dirs were created in a previous run)
    for r in domain_results:
        domain = r["domain"]
        if f"## {domain}" not in content and not r.get("skipped"):
            content += f"\n## {domain}\n\n"
            content += "| Date | Topic | Key Finding | Path |\n"
            content += "|------|-------|-------------|------|\n"
            content += f"| (auto-created) | (new domain) | Synthesized from {r.get('articles_processed', 0)} articles | `{domain}/` |\n"

    if not dry_run:
        index_dst.parent.mkdir(parents=True, exist_ok=True)
        index_dst.write_text(content, encoding="utf-8")


# ---------------------------------------------------------------------------
# Worktree management
# ---------------------------------------------------------------------------
def _get_worktree_branch() -> str:
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    return f"jarvis/knowledge-consolidation-{today}"


def _create_worktree() -> Path | None:
    """Create a git worktree for consolidation output. Returns worktree path."""
    sys.path.insert(0, str(REPO_ROOT))
    from tools.scripts.lib.worktree import worktree_setup  # noqa: E402
    branch = _get_worktree_branch()
    wt = worktree_setup(branch, worktree_dir=WORKTREE_DIR, symlink_memory=False)
    return wt


def _commit_worktree(state: dict) -> bool:
    """Commit worktree changes and merge to main. Returns True on success."""
    wt_path_str = state.get("active_worktree")
    branch = state.get("active_branch")
    if not wt_path_str or not branch:
        print("No active worktree found in state. Run without --commit first.")
        return False

    wt = Path(wt_path_str)
    if not wt.exists():
        print(f"Worktree path {wt} no longer exists.")
        return False

    # 1. Commit in worktree
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    msg = f"feat(knowledge): domain consolidation {today}"
    result = subprocess.run(
        ["git", "add", "-A"],
        capture_output=True, text=True, encoding="utf-8", errors="replace",
        cwd=str(wt),
    )
    if result.returncode != 0:
        print(f"git add failed: {result.stderr.strip()}", file=sys.stderr)
        return False

    result = subprocess.run(
        ["git", "commit", "-m", msg],
        capture_output=True, text=True, encoding="utf-8", errors="replace",
        cwd=str(wt),
    )
    if result.returncode != 0 and "nothing to commit" not in result.stdout + result.stderr:
        print(f"git commit failed: {result.stderr.strip()}", file=sys.stderr)
        return False

    # 2. Merge to main
    result = subprocess.run(
        ["git", "merge", "--ff-only", branch],
        capture_output=True, text=True, encoding="utf-8", errors="replace",
        cwd=str(REPO_ROOT),
    )
    if result.returncode != 0:
        # Try regular merge if fast-forward fails
        result = subprocess.run(
            ["git", "merge", branch, "--no-edit"],
            capture_output=True, text=True, encoding="utf-8", errors="replace",
            cwd=str(REPO_ROOT),
        )
        if result.returncode != 0:
            print(f"git merge failed: {result.stderr.strip()}", file=sys.stderr)
            print("  Manual resolution required. Worktree left intact.")
            return False

    print(f"  Merged branch {branch} into main.")

    # 3. Remove worktree safely
    sys.path.insert(0, str(REPO_ROOT))
    from tools.scripts.lib.worktree import _safe_worktree_remove  # noqa: E402
    _safe_worktree_remove(wt)

    # 4. Delete branch
    subprocess.run(
        ["git", "branch", "-D", branch],
        capture_output=True, text=True, encoding="utf-8", errors="replace",
        cwd=str(REPO_ROOT),
    )

    print("  Worktree removed. Knowledge consolidation committed to main.")
    return True


def _reject_worktree(domain: str | None, state: dict) -> bool:
    """Discard worktree (all or one domain). Returns True on success."""
    wt_path_str = state.get("active_worktree")
    branch = state.get("active_branch")
    if not wt_path_str:
        print("No active worktree found in state.")
        return False

    wt = Path(wt_path_str)

    if domain:
        # Remove just that domain's files from the worktree
        domain_dir = wt / "memory" / "knowledge" / domain
        if domain_dir.exists():
            import shutil
            shutil.rmtree(domain_dir)
            print(f"  Rejected proposals for domain '{domain}' from worktree.")
        else:
            print(f"  No proposals found for domain '{domain}' in worktree.")
        return True

    # --reject-all: remove entire worktree
    if not wt.exists():
        print(f"Worktree {wt} already absent.")
    else:
        sys.path.insert(0, str(REPO_ROOT))
        from tools.scripts.lib.worktree import _safe_worktree_remove  # noqa: E402
        _safe_worktree_remove(wt)
        # Delete branch
        if branch:
            subprocess.run(
                ["git", "branch", "-D", branch],
                capture_output=True, text=True, encoding="utf-8", errors="replace",
                cwd=str(REPO_ROOT),
            )
        print("  All proposals rejected. Worktree removed.")

    return True


# ---------------------------------------------------------------------------
# Health signal
# ---------------------------------------------------------------------------
def _emit_health_signal(status: str, domains_processed: int, error: str = "") -> None:
    """Write a health signal to memory/learning/signals/."""
    SIGNALS_DIR.mkdir(parents=True, exist_ok=True)
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    signal_file = SIGNALS_DIR / f"{today}_domain-consolidator-health.md"

    # Don't append duplicate signals for same day -- update in place
    rating = 7 if status == "success" else 4
    content = (
        f"# Domain Consolidator Health -- {today}\n\n"
        f"- status: {status}\n"
        f"- domains_processed: {domains_processed}\n"
        f"- timestamp: {datetime.now(timezone.utc).isoformat()}\n"
    )
    if error:
        content += f"- error: {error}\n"
        rating = 3
    content += f"- rating: {rating}\n"
    content += "- producer: domain_consolidator\n"

    try:
        signal_file.write_text(content, encoding="utf-8")
    except OSError as exc:
        print(f"  WARN: could not write health signal: {exc}", file=sys.stderr)


# ---------------------------------------------------------------------------
# Main consolidation run
# ---------------------------------------------------------------------------
def run_consolidation(dry_run: bool = False, autonomous: bool = False) -> int:
    """Main consolidation run. Returns exit code."""
    print("Domain Knowledge Consolidator")
    print(f"  Mode: {'dry-run' if dry_run else 'autonomous' if autonomous else 'interactive'}")
    print(f"  Date: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}")
    print()

    state = _load_state()
    existing_domains = _detect_domains(state)
    print(f"Existing domains: {existing_domains}")

    # --- Worktree setup ---
    if not dry_run:
        wt = _create_worktree()
        if wt is None:
            print("ERROR: failed to create worktree -- aborting", file=sys.stderr)
            _emit_health_signal("failed", 0, "worktree creation failed")
            return 1
        state["active_worktree"] = str(wt)
        state["active_branch"] = _get_worktree_branch()
        output_base = wt  # all outputs go here
    else:
        output_base = REPO_ROOT  # dry-run: would go here
        wt = None

    # --- Detect new domain proposals ---
    new_domain_proposals = _propose_new_domains(existing_domains)
    if new_domain_proposals:
        print(f"\nProposed new domains: {[p['domain'] for p in new_domain_proposals]}")

    # --- Detect retirement candidates ---
    retirement_candidates = _check_retirement_candidates(existing_domains, state)
    if retirement_candidates:
        print(f"Proposed retirements: {[c['domain'] for c in retirement_candidates]}")

    # --- Process new domain proposals (create dirs + synthesize) ---
    # Add proposed domains to the processing list
    all_domains_to_process = existing_domains[:]
    for proposal in new_domain_proposals:
        domain = proposal["domain"]
        if domain not in all_domains_to_process:
            all_domains_to_process.append(domain)
            # Create domain dir in main repo knowledge dir (so source reads work)
            new_dir = KNOWLEDGE_DIR / domain
            if not new_dir.exists() and not dry_run:
                new_dir.mkdir(parents=True, exist_ok=True)

    # --- Per-domain synthesis ---
    domain_results: list[dict] = []
    errors: list[str] = []

    for domain in all_domains_to_process:
        print(f"\n[{domain}]")
        new_sources, already_incorporated = _gather_sources(domain, state, dry_run=dry_run)

        if not new_sources:
            print("  No new sources -- skipping")
            domain_results.append({
                "domain": domain,
                "articles_processed": 0,
                "subdomains": [],
                "contradictions": [],
                "context_chars": 0,
                "skipped": True,
            })
            continue

        # Read existing context for incremental update
        existing_context = ""
        ctx_file = KNOWLEDGE_DIR / domain / "_context.md"
        if ctx_file.exists():
            existing_context = ctx_file.read_text(encoding="utf-8", errors="replace")

        if dry_run:
            print(f"  Would synthesize {len(new_sources)} new sources")
            domain_results.append({
                "domain": domain,
                "articles_processed": len(new_sources),
                "subdomains": [],
                "contradictions": [],
                "context_chars": 0,
            })
            continue

        # LLM synthesis — batch large domains to stay within prompt limits
        print(f"  Synthesizing {len(new_sources)} sources via Claude Sonnet...")
        if len(new_sources) > _MAX_ARTICLES_PER_BATCH:
            result = _synthesize_batched(domain, new_sources, existing_context)
        else:
            prompt = _build_synthesis_prompt(domain, new_sources, existing_context)
            result = _call_llm(prompt)

        if result is None:
            errors.append(f"{domain}: LLM synthesis failed")
            domain_results.append({
                "domain": domain,
                "articles_processed": len(new_sources),
                "subdomains": [],
                "contradictions": [],
                "context_chars": 0,
                "error": "LLM synthesis failed",
            })
            continue

        # Write outputs to worktree
        domain_out_dir = output_base / "memory" / "knowledge" / domain

        # _context.md
        context_content = result.get("context_md", f"# {domain.title()} Domain Knowledge\n\n(synthesis failed)")
        context_chars = _write_context_md(domain_out_dir, context_content, dry_run=False)
        print(f"  _context.md: {context_chars} chars")

        # Sub-domain files
        subdomains_written = []
        caveats_map = result.get("caveats_per_subdomain", {})
        for sd in result.get("subdomains", []):
            name = sd.get("name", "unknown")
            content = sd.get("content", "")
            caveats = caveats_map.get(name, [])
            chars = _write_subdomain_file(domain_out_dir, name, content, caveats, dry_run=False)
            subdomains_written.append({"name": name, "title": sd.get("title", name), "chars": chars})
            print(f"  {name}.md: {chars} chars")

        # Prune stale sub-domain files (slug drift: LLM may rename across runs)
        new_names = {s["name"] for s in subdomains_written}
        old_names = state.get(domain, {}).get("subdomain_files", [])
        for stale in old_names:
            if stale not in new_names:
                stale_path = domain_out_dir / f"{stale}.md"
                if stale_path.exists():
                    stale_path.unlink()
                    print(f"  PRUNED stale: {stale}.md")

        # Update state
        all_source_paths = already_incorporated + [s["path"] for s in new_sources]
        state.setdefault(domain, {})
        state[domain]["last_consolidated"] = datetime.now(timezone.utc).isoformat()
        state[domain]["incorporated_files"] = all_source_paths
        state[domain]["subdomain_files"] = [s["name"] for s in subdomains_written]

        domain_results.append({
            "domain": domain,
            "articles_processed": len(new_sources),
            "subdomains": subdomains_written,
            "contradictions": result.get("contradictions", []),
            "context_chars": context_chars,
        })

    # --- Write _consolidation_report.md ---
    print("\nWriting consolidation report...")
    report_path = _write_consolidation_report(
        output_base / "memory" / "knowledge",
        domain_results,
        new_domain_proposals,
        retirement_candidates,
        dry_run=dry_run,
    )
    print(f"  Report: {report_path}")

    # --- Update index.md ---
    if not dry_run:
        _update_index_md(output_base, new_domain_proposals, domain_results, dry_run=False)
        print("  index.md updated")

    # --- Save state ---
    if not dry_run:
        _save_state(state)

    # --- Slack notification ---
    total_processed = sum(r.get("articles_processed", 0) for r in domain_results)
    total_subdomains = sum(len(r.get("subdomains", [])) for r in domain_results)
    total_contradictions = sum(len(r.get("contradictions", [])) for r in domain_results)
    slack_msg = (
        f"Domain Consolidator: {len(domain_results)} domains processed, "
        f"{total_processed} new articles, {total_subdomains} sub-domains proposed, "
        f"{len(new_domain_proposals)} taxonomy changes, {total_contradictions} contradictions. "
        f"Review: memory/knowledge/_consolidation_report.md"
    )
    if dry_run:
        print(f"\nSlack (dry-run, not sent): {slack_msg}")
    else:
        _send_slack(slack_msg, errors)

    # --- Health signal ---
    status = "failed" if errors else "success"
    if not dry_run:
        _emit_health_signal(status, len(domain_results), "; ".join(errors))
        _emit_producer_run(status, len(domain_results))

    print(f"\nDone. Status: {status}")
    if errors:
        print("Errors:")
        for e in errors:
            print(f"  - {e}")
    if not dry_run and wt:
        print(f"\nProposal ready at: {wt}")
        print("Review the consolidation report, then run:")
        print("  python tools/scripts/domain_knowledge_consolidator.py --commit")
        print("  python tools/scripts/domain_knowledge_consolidator.py --reject-all")

    return 1 if errors else 0


def _send_slack(msg: str, errors: list[str]) -> None:
    """Send Slack notification via slack_notify.py."""
    try:
        sys.path.insert(0, str(REPO_ROOT))
        from tools.scripts.slack_notify import notify  # noqa: E402
        # Ensure ASCII-safe
        safe_msg = msg.encode("ascii", errors="replace").decode("ascii")
        notify(safe_msg, severity="routine")
    except Exception as exc:
        print(f"  WARN: Slack notification failed: {exc}", file=sys.stderr)


def _emit_producer_run(status: str, domains_processed: int) -> None:
    """Write producer run record to manifest_db."""
    try:
        sys.path.insert(0, str(REPO_ROOT))
        from tools.scripts.manifest_db import write_producer_run  # noqa: E402
        now = datetime.now(timezone.utc).isoformat()
        write_producer_run(
            producer="domain_consolidator",
            run_date=datetime.now(timezone.utc).strftime("%Y-%m-%d"),
            started_at=now,
            completed_at=now,
            status=status,
            artifact_count=domains_processed,
        )
    except Exception:
        pass


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------
def main() -> int:
    parser = argparse.ArgumentParser(description="Domain Knowledge Consolidator")
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--dry-run", action="store_true",
                       help="Show plan without writing files or calling LLM")
    group.add_argument("--autonomous", action="store_true",
                       help="Full run: create worktree, synthesize, write, notify Slack")
    group.add_argument("--commit", action="store_true",
                       help="Merge worktree proposals into main tree")
    group.add_argument("--reject", metavar="DOMAIN",
                       help="Reject proposals for a specific domain")
    group.add_argument("--reject-all", action="store_true",
                       help="Reject all proposals and remove worktree")
    args = parser.parse_args()

    if args.dry_run:
        return run_consolidation(dry_run=True)
    elif args.autonomous:
        return run_consolidation(autonomous=True)
    elif args.commit:
        state = _load_state()
        ok = _commit_worktree(state)
        if ok:
            # Clear active worktree from state after successful commit
            state.pop("active_worktree", None)
            state.pop("active_branch", None)
            _save_state(state)
        return 0 if ok else 1
    elif args.reject:
        state = _load_state()
        ok = _reject_worktree(args.reject, state)
        return 0 if ok else 1
    elif args.reject_all:
        state = _load_state()
        ok = _reject_worktree(None, state)
        if ok:
            state.pop("active_worktree", None)
            state.pop("active_branch", None)
            _save_state(state)
        return 0 if ok else 1
    else:
        # Default: interactive run (same as --autonomous but without Task Scheduler context)
        return run_consolidation(autonomous=True)


if __name__ == "__main__":
    sys.exit(main())
