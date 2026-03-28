#!/usr/bin/env python3
"""Validate agent definition files against the Six-Section anatomy."""

import argparse
import os
import re
import sys


REQUIRED_SECTIONS = [
    "Identity",
    "Mission",
    "Critical Rules",
    "Deliverables",
    "Workflow",
    "Success Metrics",
]

AGENTS_DIR = os.path.join(
    os.path.dirname(__file__), "..", "..", "orchestration", "agents"
)


def find_sections(content):
    """Extract h2 headings from markdown content."""
    headings = re.findall(r"^## (.+)$", content, re.MULTILINE)
    return [h.strip() for h in headings]


def check_agent(filepath):
    """Check a single agent file for required sections. Returns (name, found, missing)."""
    name = os.path.splitext(os.path.basename(filepath))[0]
    with open(filepath, "r", encoding="utf-8") as f:
        content = f.read()

    headings = find_sections(content)
    found = []
    missing = []
    for section in REQUIRED_SECTIONS:
        if any(section.lower() in h.lower() for h in headings):
            found.append(section)
        else:
            missing.append(section)

    return name, found, missing


def main():
    parser = argparse.ArgumentParser(
        description="Validate agent definitions against the Six-Section anatomy."
    )
    parser.add_argument(
        "--dir",
        default=AGENTS_DIR,
        help="Directory containing agent .md files (default: orchestration/agents/)",
    )
    parser.add_argument(
        "--verbose", "-v", action="store_true", help="Show per-agent section details"
    )
    args = parser.parse_args()

    agents_dir = os.path.normpath(args.dir)
    if not os.path.isdir(agents_dir):
        print("Error: directory not found: %s" % agents_dir)
        sys.exit(2)

    md_files = sorted(
        [f for f in os.listdir(agents_dir) if f.endswith(".md")]
    )

    if not md_files:
        print("No .md files found in %s" % agents_dir)
        sys.exit(2)

    results = []
    for md_file in md_files:
        filepath = os.path.join(agents_dir, md_file)
        name, found, missing = check_agent(filepath)
        results.append((name, found, missing))

    # Print summary table (ASCII only)
    header = "%-20s %-8s %-40s" % ("Agent", "Score", "Missing Sections")
    print(header)
    print("-" * len(header))

    all_pass = True
    for name, found, missing in results:
        score = "%d/6" % len(found)
        missing_str = ", ".join(missing) if missing else "(none)"
        print("%-20s %-8s %-40s" % (name, score, missing_str))
        if args.verbose and found:
            print("  Found: %s" % ", ".join(found))
        if missing:
            all_pass = False

    print()
    print("Agents checked: %d" % len(results))
    print("Required sections: %s" % ", ".join(REQUIRED_SECTIONS))

    if all_pass:
        print("Result: ALL PASS")
        sys.exit(0)
    else:
        failing = [name for name, _, missing in results if missing]
        print("Result: FAIL -- %d agent(s) missing sections: %s" % (len(failing), ", ".join(failing)))
        sys.exit(1)


if __name__ == "__main__":
    main()
