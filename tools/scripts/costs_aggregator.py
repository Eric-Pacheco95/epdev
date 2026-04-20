#!/usr/bin/env python3
"""costs_aggregator.py — deterministic Claude Code cost aggregator.

Reads Claude Code transcript JSONL files across all epdev project dirs,
applies list-price token rates from config/ai_pricing.json, extracts skill
attribution via regex, and writes data/costs_rollup.json with 4 rolling
windows (7d / 30d / 90d / ytd).

No LLM calls. Run hourly via run_heartbeat.bat.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[2]

SKILL_DIRECT_RE = re.compile(r"^/([a-z][a-z0-9-]+)")
SKILL_TAG_RE = re.compile(r"<command-name>/?([a-z][a-z0-9-]+)</command-name>")


def load_pricing(pricing_path: Path) -> tuple[dict, float]:
    data = json.loads(pricing_path.read_text(encoding="utf-8"))
    claude = data.get("claude", {})
    return claude.get("models", {}), float(claude.get("monthly_budget_usd", 25.0))


def compute_cost(usage: dict, rates: dict) -> float:
    return (
        usage.get("input_tokens", 0) * rates.get("input_per_mtok", 0) / 1_000_000
        + usage.get("output_tokens", 0) * rates.get("output_per_mtok", 0) / 1_000_000
        + usage.get("cache_read_input_tokens", 0) * rates.get("cache_read_per_mtok", 0) / 1_000_000
        + usage.get("cache_creation_input_tokens", 0) * rates.get("cache_creation_per_mtok", 0) / 1_000_000
    )


def find_transcript_files() -> list[Path]:
    projects_dir = Path.home() / ".claude" / "projects"
    files: list[Path] = []
    for proj_dir in sorted(projects_dir.glob("C--Users-ericp-Github-*")):
        if proj_dir.is_dir():
            files.extend(sorted(proj_dir.glob("*.jsonl")))
    return files


def extract_text(content: object) -> str:
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        return " ".join(
            b.get("text", "") for b in content
            if isinstance(b, dict) and b.get("type") == "text"
        )
    return ""


def parse_session(filepath: Path, model_rates: dict) -> list[dict]:
    """Return cost events from a single transcript JSONL."""
    session_id = filepath.stem
    events: list[dict] = []
    active_skill: str | None = None

    for raw_line in filepath.read_text(encoding="utf-8", errors="replace").splitlines():
        raw_line = raw_line.strip()
        if not raw_line:
            continue
        try:
            rec = json.loads(raw_line)
        except json.JSONDecodeError:
            continue

        rtype = rec.get("type")

        if rtype == "user":
            text = extract_text(rec.get("message", {}).get("content", "")).strip()
            m = SKILL_DIRECT_RE.match(text) or SKILL_TAG_RE.search(text)
            if m:
                active_skill = "/" + m.group(1)

        elif rtype == "assistant":
            msg = rec.get("message", {})
            usage = msg.get("usage")
            model = msg.get("model", "")
            if not usage or not model:
                continue

            ts_str = rec.get("timestamp", "")
            try:
                ts = datetime.fromisoformat(ts_str.replace("Z", "+00:00"))
            except (ValueError, TypeError, AttributeError):
                continue

            rates = model_rates.get(model)
            if rates is None:
                print(f"WARN: unknown model '{model}' in {filepath.name} — cost zeroed", file=sys.stderr)
            cost = compute_cost(usage, rates) if rates else 0.0

            events.append({
                "ts": ts,
                "session_id": session_id,
                "model": model,
                "cost_usd": cost,
                "input_tokens": usage.get("input_tokens", 0),
                "output_tokens": usage.get("output_tokens", 0),
                "cache_read_tokens": usage.get("cache_read_input_tokens", 0),
                "cache_creation_tokens": usage.get("cache_creation_input_tokens", 0),
                "skill_name": active_skill,
            })

    return events


def _empty_window(budget_monthly: float) -> dict:
    return {
        "spend_usd": 0.0,
        "spend_prev_window_usd": 0.0,
        "input_tokens_total": 0,
        "output_tokens_total": 0,
        "cache_read_tokens_total": 0,
        "cache_creation_tokens_total": 0,
        "per_day_avg_usd": 0.0,
        "daily_spend_usd": [],
        "budget": {"monthly_usd": budget_monthly, "mtd_usd": 0.0, "pct": 0},
        "per_model": [],
        "per_skill": [],
        "session_rollups": {
            "avg_usd": 0.0,
            "session_count": 0,
            "most_expensive": None,
            "cost_per_1k_tokens_usd": 0.0,
        },
    }


def build_window(
    all_events: list[dict],
    cutoff: datetime,
    window_days: int,
    budget_monthly: float,
    now: datetime,
) -> dict:
    events = [e for e in all_events if e["ts"] >= cutoff]
    if not events:
        return _empty_window(budget_monthly)

    spend = sum(e["cost_usd"] for e in events)
    input_tok = sum(e["input_tokens"] for e in events)
    output_tok = sum(e["output_tokens"] for e in events)
    cache_read_tok = sum(e["cache_read_tokens"] for e in events)
    cache_creation_tok = sum(e["cache_creation_tokens"] for e in events)

    prev_cutoff = cutoff - timedelta(days=window_days)
    spend_prev = sum(e["cost_usd"] for e in all_events if prev_cutoff <= e["ts"] < cutoff)

    daily: dict[str, float] = {}
    for e in events:
        day = e["ts"].strftime("%Y-%m-%d")
        daily[day] = daily.get(day, 0.0) + e["cost_usd"]
    daily_spend = [round(v, 6) for v in daily.values()]

    # Per-model aggregation
    model_agg: dict[str, dict] = {}
    for e in events:
        m = e["model"]
        agg = model_agg.setdefault(m, {"model_id": m, "input": 0, "output": 0, "cost_usd": 0.0})
        agg["input"] += e["input_tokens"]
        agg["output"] += e["output_tokens"]
        agg["cost_usd"] += e["cost_usd"]

    per_model = sorted(model_agg.values(), key=lambda x: -x["cost_usd"])
    for v in per_model:
        v["cost_usd"] = round(v["cost_usd"], 6)
        v["share_pct"] = round(v["cost_usd"] / spend * 100) if spend > 0 else 0

    # Normalize share_pct sum to 100
    if per_model and spend > 0:
        delta = 100 - sum(v["share_pct"] for v in per_model)
        if delta != 0:
            per_model[0]["share_pct"] += delta

    # Per-skill aggregation (sorted by cost desc)
    skill_agg: dict[str, dict] = {}
    for e in events:
        s = e["skill_name"] or "uncategorized"
        agg = skill_agg.setdefault(s, {"skill_name": s, "events": 0, "cost_usd": 0.0})
        agg["events"] += 1
        agg["cost_usd"] += e["cost_usd"]

    per_skill = sorted(
        [{"skill_name": v["skill_name"], "events": v["events"], "cost_usd": round(v["cost_usd"], 6)}
         for v in skill_agg.values()],
        key=lambda x: -x["cost_usd"],
    )

    # Session rollups
    session_costs: dict[str, float] = {}
    for e in events:
        session_costs[e["session_id"]] = session_costs.get(e["session_id"], 0.0) + e["cost_usd"]

    session_count = len(session_costs)
    avg_usd = sum(session_costs.values()) / session_count if session_count > 0 else 0.0

    most_expensive = None
    if session_costs:
        top_sid = max(session_costs, key=lambda k: session_costs[k])
        most_expensive = {"session_id": top_sid, "cost_usd": round(session_costs[top_sid], 6)}

    total_tok = input_tok + output_tok + cache_read_tok + cache_creation_tok
    cost_per_1k = spend / total_tok * 1000 if total_tok > 0 else 0.0

    # MTD budget
    mtd_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    mtd_spend = sum(e["cost_usd"] for e in all_events if e["ts"] >= mtd_start)
    budget_pct = round(mtd_spend / budget_monthly * 100) if budget_monthly > 0 else 0

    return {
        "spend_usd": round(spend, 6),
        "spend_prev_window_usd": round(spend_prev, 6),
        "input_tokens_total": input_tok,
        "output_tokens_total": output_tok,
        "cache_read_tokens_total": cache_read_tok,
        "cache_creation_tokens_total": cache_creation_tok,
        "per_day_avg_usd": round(spend / max(window_days, 1), 6),
        "daily_spend_usd": daily_spend,
        "budget": {"monthly_usd": budget_monthly, "mtd_usd": round(mtd_spend, 6), "pct": budget_pct},
        "per_model": per_model,
        "per_skill": per_skill,
        "session_rollups": {
            "avg_usd": round(avg_usd, 6),
            "session_count": session_count,
            "most_expensive": most_expensive,
            "cost_per_1k_tokens_usd": round(cost_per_1k, 6),
        },
    }


def run(pricing_path: Path, output_path: Path) -> None:
    model_rates, budget_monthly = load_pricing(pricing_path)
    transcript_files = find_transcript_files()

    all_events: list[dict] = []
    for tf in transcript_files:
        try:
            all_events.extend(parse_session(tf, model_rates))
        except Exception as exc:
            print(f"WARN: skipping {tf.name}: {exc}", file=sys.stderr)

    all_events.sort(key=lambda e: e["ts"])

    now = datetime.now(timezone.utc)
    ytd_start = now.replace(month=1, day=1, hour=0, minute=0, second=0, microsecond=0)
    actual_days_ytd = max((now - ytd_start).days, 1)

    window_specs = {
        "7d":  (now - timedelta(days=7),  7),
        "30d": (now - timedelta(days=30), 30),
        "90d": (now - timedelta(days=90), 90),
        "ytd": (ytd_start,               actual_days_ytd),
    }

    windows = {
        key: build_window(all_events, cutoff, days, budget_monthly, now)
        for key, (cutoff, days) in window_specs.items()
    }

    any_data = any(w["session_rollups"]["session_count"] > 0 for w in windows.values())
    recent_data = any(
        windows[k]["session_rollups"]["session_count"] > 0 for k in ["7d", "30d"]
    )

    if not all_events:
        status = "empty_data"
    elif not recent_data and any_data:
        status = "partial"
    else:
        status = "ok"

    rollup = {
        "generated_at": now.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "source_transcript_count": len(transcript_files),
        "source_event_count": len(all_events),
        "windows": windows,
        "status": status,
    }

    output_path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = output_path.with_suffix(".json.tmp")
    tmp_path.write_text(json.dumps(rollup, indent=2), encoding="utf-8")
    tmp_path.replace(output_path)
    print(
        f"costs_rollup.json written: {len(transcript_files)} transcripts, "
        f"{len(all_events)} events, status={status}"
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="Aggregate Claude Code costs from transcripts")
    parser.add_argument("--output", default=str(ROOT_DIR / "data" / "costs_rollup.json"),
                        help="Output path for costs_rollup.json")
    parser.add_argument("--pricing", default=str(ROOT_DIR / "config" / "ai_pricing.json"),
                        help="Path to ai_pricing.json")
    args = parser.parse_args()

    try:
        run(Path(args.pricing), Path(args.output))
    except (FileNotFoundError, KeyError, json.JSONDecodeError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
