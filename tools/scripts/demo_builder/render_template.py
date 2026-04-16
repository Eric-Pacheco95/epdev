"""
render_template.py — Parameterized render script template for PAI CLI demos.

Usage: copy this file as render_<project>.py, fill in BRAND and SCENES,
then run: python tools/scripts/demo_builder/render_<project>.py [--scene N]
                                                                  [--assemble-only]
                                                                  [--dry-run]

Architecture notes:
  - Each project gets its own render script — no monolithic render file
  - Transition types are determined by XFADE_RULES lookup table (not manual planning)
  - Brand tokens are defined once at the top; the render script lints for consistency
  - Scenes must have matching Remotion composition IDs in src/compositions/<project>.tsx
  - snapFromFull=true in the composition is required when xfade_type == "zoomin"
"""

import argparse
import subprocess
import sys
from pathlib import Path

REPO_ROOT    = Path(__file__).parent.parent.parent.parent.resolve()
REMOTION_DIR = REPO_ROOT / "remotion"
SEGMENTS_DIR = REPO_ROOT / "tools/scripts/demo_builder/output/segments"

# ─── Brand config (fill in for each project) ─────────────────────────────────
BRAND = {
    "name":          "PAI",           # Display name in logs
    "prompt_prefix": "pai > ",        # CLI prompt shown in terminal scenes
    "project_slug":  "my-demo",       # Used in output filename
    "output_dir":    REPO_ROOT / "memory/work/my-demo",
}
OUTPUT_PATH = BRAND["output_dir"] / f"{BRAND['project_slug']}_demo_2026-04-15.mp4"

# ─── Scene manifest ───────────────────────────────────────────────────────────
# id: must match the Composition id in src/compositions/<project>.tsx
# duration_s: used for xfade offset calculation and plan display
# component_type: drives automatic transition type selection via XFADE_RULES
#   "floating"     -> FloatingCard scene
#   "three_panel"  -> ThreePanelScene (requires snapFromFull=true in composition)
SCENES = [
    # {"order": 1, "id": "my-demo-hook-01",     "duration_s": 8,  "component_type": "floating"},
    # {"order": 2, "id": "my-demo-observe-02",  "duration_s": 15, "component_type": "floating"},
    # {"order": 3, "id": "my-demo-arch-03",     "duration_s": 22, "component_type": "three_panel"},
    # ... add scenes here
]

# ─── Transition rules (deterministic — do not edit per-project) ──────────────
# Determines xfade type from scene boundary types.
# Priority: first matching rule wins.
#
# Rule format: (outgoing_type, incoming_type) -> (xfade_type, duration_s)
#
# "zoomin" + incoming ThreePanelScene: requires snapFromFull=true in the
# composition. The xfade zooms into the outgoing terminal, then the new
# scene's full-width terminal compresses left as the right panel slides in.
XFADE_RULES = {
    ("floating",     "three_panel"): ("zoomin",    1.0),   # zoom into CLI -> snap to left
    ("three_panel",  "floating"):    ("fadeblack",  0.8),   # chapter break out of three-panel
    ("three_panel",  "three_panel"): ("fadeblack",  0.8),   # chapter break between three-panels
    ("floating",     "floating"):    ("fade",       0.8),   # default continuity
}
XFADE_DEFAULT = ("dissolve", 0.8)                          # fallback for unknown type combos


def get_transition(out_type: str, in_type: str) -> tuple[str, float]:
    return XFADE_RULES.get((out_type, in_type), XFADE_DEFAULT)


def build_transitions(scenes: list) -> list[tuple[str, float]]:
    """Derive transition list from scene component_type pairs. No manual editing needed."""
    ordered = sorted(scenes, key=lambda s: s["order"])
    return [
        get_transition(ordered[i]["component_type"], ordered[i + 1]["component_type"])
        for i in range(len(ordered) - 1)
    ]


TRANSITIONS = build_transitions(SCENES) if SCENES else []


def segment_path(scene: dict) -> Path:
    return SEGMENTS_DIR / f"ready_{scene['order']:02d}_{scene['id']}.mp4"


def brand_lint(scenes: list) -> list[str]:
    """
    Pre-render brand audit: check for hardcoded brand strings that should use
    BRAND config. Returns list of warnings (empty = clean).

    Extend this list if your project has additional brand tokens to guard.
    """
    warnings = []
    # Add project-specific patterns to check here, e.g.:
    # if any("jarvis" in s["id"].lower() for s in scenes):
    #     warnings.append("Scene ID contains 'jarvis' — should use brand slug")
    return warnings


def render_scene(scene: dict) -> int:
    out = segment_path(scene)
    out.parent.mkdir(parents=True, exist_ok=True)
    cmd = [
        "npx", "remotion", "render",
        "src/index.ts",
        scene["id"],
        str(out),
        "--codec=h264",
        "--pixel-format=yuv420p",
        "--crf=18",
    ]
    print(f"  [render] {scene['id']} -> {out.name}")
    result = subprocess.run(cmd, cwd=REMOTION_DIR, shell=True)
    return result.returncode


def build_xfade_filter(scenes: list, transitions: list) -> tuple[str, float]:
    """Build FFmpeg -filter_complex string chaining xfade transitions."""
    ordered = sorted(scenes, key=lambda s: s["order"])
    parts = []
    stream_dur = float(ordered[0]["duration_s"])
    prev_out = "0:v"

    for i, (trans_type, trans_dur) in enumerate(transitions):
        offset = stream_dur - trans_dur
        curr_in = f"{i + 1}:v"
        next_out = f"v{i}" if i < len(transitions) - 1 else "vout"
        parts.append(
            f"[{prev_out}][{curr_in}]"
            f"xfade=transition={trans_type}:duration={trans_dur:.2f}:offset={offset:.3f}"
            f"[{next_out}]"
        )
        stream_dur = stream_dur + ordered[i + 1]["duration_s"] - trans_dur
        prev_out = next_out

    return ";".join(parts), stream_dur


def assemble_with_xfade(scenes: list, transitions: list) -> int:
    ordered = sorted(scenes, key=lambda s: s["order"])
    present = [s for s in ordered if segment_path(s).exists()]
    missing = [s for s in ordered if not segment_path(s).exists()]

    if missing:
        print(f"[WARN] Missing: {[s['id'] for s in missing]}")
        if len(missing) == len(ordered):
            print("[ERROR] No segments to assemble.")
            return 1
        print("[WARN] Missing segments — falling back to simple concat (no xfade).")
        return _simple_concat(present)

    inputs = []
    for s in ordered:
        inputs.extend(["-i", str(segment_path(s))])

    filter_str, total_dur = build_xfade_filter(ordered, transitions)
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    cmd = (
        ["ffmpeg", "-y"]
        + inputs
        + [
            "-filter_complex", filter_str,
            "-map", "[vout]",
            "-c:v", "libx264",
            "-preset", "fast",
            "-crf", "18",
            "-pix_fmt", "yuv420p",
            "-movflags", "+faststart",
            str(OUTPUT_PATH),
        ]
    )
    print(f"\n[assemble] {len(ordered)} segments + xfade -> {OUTPUT_PATH.name}  (~{total_dur:.0f}s)")
    result = subprocess.run(cmd)
    return result.returncode


def _simple_concat(scenes: list) -> int:
    concat_file = SEGMENTS_DIR / "concat_fallback.txt"
    with open(concat_file, "w") as f:
        for s in scenes:
            f.write(f"file '{segment_path(s)}'\n")
    cmd = [
        "ffmpeg", "-y",
        "-f", "concat", "-safe", "0",
        "-i", str(concat_file),
        "-c:v", "libx264", "-preset", "fast", "-crf", "18",
        "-pix_fmt", "yuv420p", "-movflags", "+faststart",
        str(OUTPUT_PATH),
    ]
    return subprocess.run(cmd).returncode


def print_plan(transitions: list):
    total_raw = sum(s["duration_s"] for s in SCENES)
    total_transition = sum(d for _, d in transitions)
    print("\n" + "=" * 72)
    print(f"  {BRAND['name']} DEMO — scene plan  (auto-derived xfade transitions)")
    print(f"  Scenes: {len(SCENES)}   Transitions: {len(transitions)}")
    print("=" * 72)
    print(f"  Raw total: {total_raw}s  |  Transition overlap: {total_transition:.1f}s  |  "
          f"Output: ~{total_raw - total_transition:.0f}s")
    print("-" * 72)
    t = 0.0
    ordered = sorted(SCENES, key=lambda s: s["order"])
    for i, s in enumerate(ordered):
        end = t + s["duration_s"]
        m0, s0 = divmod(int(t), 60)
        m1, s1 = divmod(int(end), 60)
        trans_str = f"  -> {transitions[i][0]} {transitions[i][1]:.1f}s" if i < len(transitions) else ""
        ctype = f"[{s['component_type']}]"
        print(f"  {s['order']:2d}  {m0}:{s0:02d}-{m1}:{s1:02d}  ({s['duration_s']:2d}s)  {ctype:<14}  {s['id']}{trans_str}")
        t = end
    print("=" * 72 + "\n")


def main():
    parser = argparse.ArgumentParser(description=f"Render {BRAND['name']} demo video")
    parser.add_argument("--scene",         type=int,            help="Render single scene by order number")
    parser.add_argument("--assemble-only", action="store_true", help="Skip rendering, only assemble")
    parser.add_argument("--dry-run",       action="store_true", help="Print plan only")
    args = parser.parse_args()

    if not SCENES:
        print("[ERROR] SCENES list is empty. Fill in the scene manifest before running.")
        sys.exit(1)

    transitions = build_transitions(SCENES)
    print_plan(transitions)

    # Brand lint before any rendering
    lint_warnings = brand_lint(SCENES)
    if lint_warnings:
        print("[BRAND LINT]")
        for w in lint_warnings:
            print(f"  WARN: {w}")
        print()

    if args.dry_run:
        return

    if args.scene:
        target = next((s for s in SCENES if s["order"] == args.scene), None)
        if not target:
            print(f"[ERROR] No scene with order {args.scene}")
            sys.exit(1)
        sys.exit(render_scene(target))

    if not args.assemble_only:
        print("[render] Rendering all scenes...\n")
        failed = []
        for scene in sorted(SCENES, key=lambda s: s["order"]):
            rc = render_scene(scene)
            if rc != 0:
                failed.append(scene["id"])
        if failed:
            print(f"\n[WARN] {len(failed)} scene(s) failed: {failed}")

    rc = assemble_with_xfade(SCENES, transitions)
    if rc == 0 and OUTPUT_PATH.exists():
        size_mb = OUTPUT_PATH.stat().st_size / (1024 * 1024)
        print(f"\n[DONE] {OUTPUT_PATH}")
        print(f"       {size_mb:.1f} MB")
    else:
        print("[ERROR] Assembly failed.")
        sys.exit(1)


if __name__ == "__main__":
    main()
