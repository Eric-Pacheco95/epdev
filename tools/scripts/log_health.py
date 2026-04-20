#!/usr/bin/env python3
import argparse
import json
from datetime import date
from pathlib import Path

DATA_FILE = Path(__file__).resolve().parents[2] / "data" / "health.jsonl"

parser = argparse.ArgumentParser(description="Log a daily health entry to data/health.jsonl")
parser.add_argument("--gym", type=int, required=True, help="Gym sessions today")
parser.add_argument("--sleep", type=float, required=True, help="Average sleep hours")
parser.add_argument("--energy", type=int, required=True, help="Subjective energy 1-5")
parser.add_argument("--notes", type=str, default="", help="Optional notes")
args = parser.parse_args()

if not 1 <= args.energy <= 5:
    raise SystemExit(f"Error: --energy must be 1-5, got {args.energy}")

entry = {
    "date": date.today().isoformat(),
    "gym_sessions": args.gym,
    "sleep_avg_hours": args.sleep,
    "subjective_energy": args.energy,
}
if args.notes:
    entry["notes"] = args.notes

DATA_FILE.parent.mkdir(parents=True, exist_ok=True)
with DATA_FILE.open("a") as f:
    f.write(json.dumps(entry) + "\n")

print(f"Logged: {json.dumps(entry)}")
