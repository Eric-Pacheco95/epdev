#!/usr/bin/env python3
"""Nightly finance recap -- Questrade positions + manual TD positions -> Slack #finance.

Reads:
  - Questrade API (positions, balances via lib/questrade.py)
  - data/positions.yaml (manual TD positions)
  - data/predictions/*trade-plan*.md (active trade plans for cross-reference)

Posts:
  - Nightly recap to Slack #finance channel
  - Alerts if leveraged ETF positions exceed max hold days
  - Warns if Questrade token is approaching expiry (>48h since refresh)

Usage:
  python tools/scripts/finance_recap.py              # post to Slack
  python tools/scripts/finance_recap.py --dry-run     # print to terminal only
  python tools/scripts/finance_recap.py --json        # output raw JSON (for other consumers)
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import yaml

_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(_ROOT))

from tools.scripts.lib.questrade import QuestradeClient, QuestradeAuthError
from tools.scripts.slack_notify import notify

# Slack channel for finance recaps -- will be created on first use
FINANCE_CHANNEL = "C0AR8NGHK9S"  # #finance

POSITIONS_FILE = _ROOT / "data" / "positions.yaml"
PREDICTIONS_DIR = _ROOT / "data" / "predictions"

# Known leveraged/inverse ETFs and their decay characteristics
LEVERAGED_ETFS = {
    "NRGU": {"leverage": 3, "type": "bull", "underlying": "US Big Oil"},
    "NRGD": {"leverage": 3, "type": "bear", "underlying": "US Big Oil"},
    "UCO": {"leverage": 2, "type": "bull", "underlying": "Crude Oil"},
    "SCO": {"leverage": 2, "type": "bear", "underlying": "Crude Oil"},
    "TQQQ": {"leverage": 3, "type": "bull", "underlying": "Nasdaq 100"},
    "SQQQ": {"leverage": 3, "type": "bear", "underlying": "Nasdaq 100"},
    "SPXU": {"leverage": 3, "type": "bear", "underlying": "S&P 500"},
    "SDS": {"leverage": 2, "type": "bear", "underlying": "S&P 500"},
    "UVXY": {"leverage": 1.5, "type": "bull", "underlying": "VIX"},
    "SOXL": {"leverage": 3, "type": "bull", "underlying": "Semiconductors"},
    "SOXS": {"leverage": 3, "type": "bear", "underlying": "Semiconductors"},
}


def load_manual_positions() -> list[dict]:
    """Load manually tracked positions from YAML."""
    if not POSITIONS_FILE.exists():
        return []
    data = yaml.safe_load(POSITIONS_FILE.read_text(encoding="utf-8"))
    positions = []
    for acct_name, acct_data in (data or {}).get("accounts", {}).items():
        for pos in acct_data.get("positions", []):
            pos["account"] = acct_name
            pos["source"] = "manual"
            positions.append(pos)
    return positions


def load_questrade_positions(client: QuestradeClient) -> list[dict]:
    """Load positions from all Questrade accounts."""
    positions = []
    accounts = client.get_accounts()
    for acct in accounts:
        acct_id = acct.get("number", "")
        acct_type = acct.get("type", "unknown")
        raw_positions = client.get_positions(acct_id)
        for pos in raw_positions:
            if pos.get("openQuantity", 0) == 0:
                continue
            ticker = pos.get("symbol", "???")
            positions.append({
                "ticker": ticker,
                "shares": pos.get("openQuantity", 0),
                "entry_price": pos.get("averageEntryPrice", 0),
                "current_price": pos.get("currentPrice", 0),
                "current_value": pos.get("currentMarketValue", 0),
                "open_pnl": pos.get("openPnl", 0),
                "open_pnl_pct": (
                    (pos.get("openPnl", 0) / (pos.get("totalCost", 1) or 1)) * 100
                ),
                "account": f"QT-{acct_type}",
                "account_id": acct_id,
                "source": "questrade",
                "leveraged": ticker in LEVERAGED_ETFS,
            })
    return positions


def load_active_trade_plans() -> list[dict]:
    """Load trade plans with status: open."""
    plans = []
    if not PREDICTIONS_DIR.exists():
        return plans
    for f in PREDICTIONS_DIR.glob("*trade-plan*.md"):
        text = f.read_text(encoding="utf-8", errors="replace")
        if "status: open" in text[:500]:
            plans.append({"file": f.name, "content": text[:2000]})
    return plans


def calc_hold_days(entry_date_str: str) -> int:
    """Calculate trading days held (approximate — counts calendar days)."""
    try:
        entry = datetime.strptime(entry_date_str, "%Y-%m-%d")
        delta = datetime.now() - entry
        return delta.days
    except (ValueError, TypeError):
        return 0


def format_recap(
    qt_positions: list[dict],
    manual_positions: list[dict],
    trade_plans: list[dict],
    token_age_hours: float,
) -> str:
    """Format the nightly recap message for Slack."""
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    lines = [f"*Finance Recap* -- {now}", ""]

    # Token health warning
    if token_age_hours > 48:
        lines.append(
            f":warning: Questrade token last refreshed {token_age_hours:.0f}h ago "
            f"(expires at 72h). Run finance_recap.py to refresh."
        )
        lines.append("")

    # Questrade positions
    if qt_positions:
        lines.append("*Questrade Positions*")
        for pos in qt_positions:
            pnl_sign = "+" if pos["open_pnl"] >= 0 else ""
            pnl_emoji = ":chart_with_upwards_trend:" if pos["open_pnl"] >= 0 else ":chart_with_downwards_trend:"
            lev_tag = ""
            if pos.get("leveraged") and pos["ticker"] in LEVERAGED_ETFS:
                info = LEVERAGED_ETFS[pos["ticker"]]
                lev_tag = f" [{info['leverage']}x {info['type']}]"
            lines.append(
                f"  {pnl_emoji} *{pos['ticker']}*{lev_tag} | "
                f"{pos['shares']} shares @ ${pos['entry_price']:.2f} | "
                f"Now: ${pos['current_price']:.2f} | "
                f"P&L: {pnl_sign}${pos['open_pnl']:.2f} ({pnl_sign}{pos['open_pnl_pct']:.1f}%)"
            )
        lines.append("")

    # Manual (TD) positions
    if manual_positions:
        lines.append("*TD Positions* (manual)")
        for pos in manual_positions:
            ticker = pos.get("ticker", "???")
            entry = pos.get("entry_price", 0)
            stop = pos.get("stop", 0)
            target = pos.get("target", 0)
            hold_days = calc_hold_days(pos.get("entry_date", ""))
            max_hold = pos.get("max_hold_days", 999)
            lev_tag = ""
            alerts = []

            if pos.get("leveraged") and ticker in LEVERAGED_ETFS:
                info = LEVERAGED_ETFS[ticker]
                lev_tag = f" [{info['leverage']}x {info['type']}]"

            if hold_days > max_hold:
                alerts.append(f":rotating_light: OVER MAX HOLD ({hold_days}/{max_hold}d)")
            elif hold_days > max_hold * 0.7:
                alerts.append(f":warning: approaching max hold ({hold_days}/{max_hold}d)")

            alert_str = " ".join(alerts)
            plan_ref = pos.get("trade_plan", "")
            plan_tag = f" | Plan: {plan_ref}" if plan_ref else ""

            lines.append(
                f"  *{ticker}*{lev_tag} | "
                f"Entry: ${entry:.2f} | Stop: ${stop:.2f} | Target: ${target:.2f} | "
                f"Day {hold_days}{plan_tag}"
            )
            if alert_str:
                lines.append(f"    {alert_str}")
        lines.append("")

    # Summary
    total_qt = len(qt_positions)
    total_manual = len(manual_positions)
    total_leveraged = sum(
        1 for p in qt_positions + manual_positions if p.get("leveraged")
    )
    active_plans = len(trade_plans)

    lines.append(
        f"_Positions: {total_qt} Questrade + {total_manual} TD = "
        f"{total_qt + total_manual} total "
        f"({total_leveraged} leveraged) | {active_plans} active trade plan(s)_"
    )

    if not qt_positions and not manual_positions:
        lines.append("_No open positions across any account._")

    # Analysis section (populated by --analyze flag via claude -p)
    return "\n".join(lines)


def build_analysis_prompt(
    qt_positions: list[dict],
    manual_positions: list[dict],
    trade_plans: list[dict],
) -> str:
    """Build a prompt for claude -p to analyze positions against context."""
    positions_summary = []
    for p in qt_positions:
        positions_summary.append(
            f"  {p['ticker']}: {p['shares']} shares, entry ${p['entry_price']:.2f}, "
            f"now ${p['current_price']:.2f}, P&L {p['open_pnl']:+.2f} ({p['open_pnl_pct']:+.1f}%)"
            f"{' [LEVERAGED]' if p.get('leveraged') else ''}"
        )
    for p in manual_positions:
        hold_days = calc_hold_days(p.get("entry_date", ""))
        positions_summary.append(
            f"  {p['ticker']}: entry ${p.get('entry_price', 0):.2f}, "
            f"stop ${p.get('stop', 0):.2f}, target ${p.get('target', 0):.2f}, "
            f"day {hold_days}/{p.get('max_hold_days', '?')}"
            f"{' [LEVERAGED ' + str(p.get('leverage_factor', '?')) + 'x]' if p.get('leveraged') else ''}"
        )

    plans_text = ""
    for plan in trade_plans:
        plans_text += f"\n--- {plan['file']} ---\n{plan['content'][:1500]}\n"

    return f"""You are analyzing Eric's live trading positions for a nightly recap.

CURRENT POSITIONS:
{chr(10).join(positions_summary)}

ACTIVE TRADE PLANS:
{plans_text if plans_text else 'None'}

TASK -- produce a brief analysis (under 300 words) covering:

1. THESIS CHECK: For each position with a trade plan, is the original thesis still valid based on what you know? Flag any where conditions have changed (e.g., deadline passed, deal announced, thesis invalidated).

2. STOP/TARGET ALERTS: Any positions near their stop or target levels? Any leveraged ETFs past their max hold period?

3. PORTFOLIO RISKS: What correlated risks exist across positions? (e.g., multiple energy-exposed names, all positions directionally aligned)

4. ACTION ITEMS: Specific things Eric should check or do tomorrow. Be direct -- "close X" or "watch Y for Z" not vague advice.

Read the following files for context before answering:
- memory/work/TELOS.md (current goals and priorities)
- data/predictions/ (any open predictions that relate to these positions)

Output as a Slack-formatted message (use *bold* and bullet points). No preamble.
"""


def run_analysis(
    qt_positions: list[dict],
    manual_positions: list[dict],
    trade_plans: list[dict],
) -> str | None:
    """Run claude -p to analyze positions. Returns analysis text or None on failure."""
    import subprocess
    import shutil

    claude_path = shutil.which("claude")
    if not claude_path:
        print("claude CLI not found -- skipping analysis", file=sys.stderr)
        return None

    prompt = build_analysis_prompt(qt_positions, manual_positions, trade_plans)

    try:
        result = subprocess.run(
            [claude_path, "-p", prompt, "--max-turns", "3"],
            capture_output=True,
            text=True,
            timeout=120,
            cwd=str(_ROOT),
            encoding="utf-8",
            errors="replace",
        )
        output = result.stdout.strip()
        # Check for rate limit (exits 0 but no useful output)
        if not output or "hit your limit" in output.lower():
            print("claude -p returned empty or rate-limited", file=sys.stderr)
            return None
        return output
    except subprocess.TimeoutExpired:
        print("claude -p timed out after 120s", file=sys.stderr)
        return None
    except Exception as e:
        print(f"claude -p failed: {e}", file=sys.stderr)
        return None


def main():
    parser = argparse.ArgumentParser(description="Nightly finance recap")
    parser.add_argument("--dry-run", action="store_true", help="Print to terminal only")
    parser.add_argument("--json", action="store_true", help="Output raw JSON")
    parser.add_argument("--analyze", action="store_true", help="Add AI analysis of positions vs TELOS/trade plans")
    args = parser.parse_args()

    # Load manual positions (always works)
    manual_positions = load_manual_positions()

    # Load Questrade positions
    qt_positions = []
    token_age = 0.0
    try:
        client = QuestradeClient()
        qt_positions = load_questrade_positions(client)
        token_age = client.token_age_hours()
    except QuestradeAuthError as e:
        print(f"Questrade auth failed: {e}", file=sys.stderr)
        print("Continuing with manual positions only.", file=sys.stderr)
        token_age = 999.0

    # Load trade plans
    trade_plans = load_active_trade_plans()

    if args.json:
        output = {
            "questrade": qt_positions,
            "manual": manual_positions,
            "trade_plans": [p["file"] for p in trade_plans],
            "token_age_hours": token_age,
        }
        print(json.dumps(output, indent=2, default=str))
        return

    recap = format_recap(qt_positions, manual_positions, trade_plans, token_age)

    # AI analysis via claude -p (cross-references TELOS, trade plans, memory)
    if args.analyze:
        print("Running AI analysis...", file=sys.stderr)
        analysis = run_analysis(qt_positions, manual_positions, trade_plans)
        if analysis:
            recap += "\n\n---\n*AI Analysis*\n" + analysis
        else:
            recap += "\n\n_AI analysis skipped (claude -p unavailable or rate-limited)_"

    if args.dry_run:
        # Strip Slack emoji for terminal readability
        clean = recap.replace(":chart_with_upwards_trend:", "+")
        clean = clean.replace(":chart_with_downwards_trend:", "-")
        clean = clean.replace(":warning:", "WARNING:")
        clean = clean.replace(":rotating_light:", "ALERT:")
        clean = clean.replace("*", "")
        clean = clean.replace("_", "")
        print(clean)
        return

    # Post to Slack
    channel = FINANCE_CHANNEL
    if channel:
        ok = notify(recap, channel=channel, severity="routine", username="Jarvis Finance")
    else:
        # Fall back to #epdev until #finance channel is created
        ok = notify(recap, severity="routine", username="Jarvis Finance")

    if ok:
        print("Recap posted to Slack")
    else:
        print("Failed to post recap -- printing to terminal instead")
        print(recap)


if __name__ == "__main__":
    main()
