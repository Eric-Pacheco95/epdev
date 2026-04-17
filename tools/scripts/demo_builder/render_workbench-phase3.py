"""
render_workbench-phase3.py — Claude Workbench enterprise AI-OS demo render script.

8-scene, 49s demo reframing /extract-harness --enterprise as an "AI Operating
System" for regulated banking teams. Captures complex multi-step work + daily
trivial work — audit-ready, PII-guarded, constitutionally scoped.

Usage:
    python tools/scripts/demo_builder/render_workbench-phase3.py --dry-run
    python tools/scripts/demo_builder/render_workbench-phase3.py --scene 3
    python tools/scripts/demo_builder/render_workbench-phase3.py
    python tools/scripts/demo_builder/render_workbench-phase3.py --assemble-only
"""

import argparse
import subprocess
import sys
from pathlib import Path

REPO_ROOT    = Path(__file__).parent.parent.parent.parent.resolve()
REMOTION_DIR = REPO_ROOT / "remotion"
SEGMENTS_DIR = REPO_ROOT / "tools/scripts/demo_builder/output/segments"

# ─── Brand config ─────────────────────────────────────────────────────────────
BRAND = {
    "name":          "Claude Workbench",
    "prompt_prefix": "workbench > ",
    "project_slug":  "workbench-phase3",
    "output_dir":    REPO_ROOT / "memory/work/workbench-phase3",
}
OUTPUT_PATH = BRAND["output_dir"] / f"{BRAND['project_slug']}_demo_2026-04-16.mp4"

# ─── Scene manifest ───────────────────────────────────────────────────────────
SCENES = [
    {"order": 1, "id": "wb3-hook-01",    "duration_s": 4, "component_type": "floating"},
    {"order": 2, "id": "wb3-problem-02", "duration_s": 6, "component_type": "floating"},
    {"order": 3, "id": "wb3-invoke-03",  "duration_s": 5, "component_type": "floating"},
    {"order": 4, "id": "wb3-os-04",      "duration_s": 9, "component_type": "three_panel"},
    {"order": 5, "id": "wb3-complex-05", "duration_s": 6, "component_type": "floating"},
    {"order": 6, "id": "wb3-trivial-06", "duration_s": 8, "component_type": "three_panel"},
    {"order": 7, "id": "wb3-output-07",  "duration_s": 6, "component_type": "floating"},
    {"order": 8, "id": "wb3-close-08",   "duration_s": 5, "component_type": "floating"},
]

# ─── Transition rules (shared with render_template.py) ───────────────────────
XFADE_RULES = {
    ("floating",     "three_panel"): ("zoomin",    1.0),
    ("three_panel",  "floating"):    ("fadeblack", 0.8),
    ("three_panel",  "three_panel"): ("fadeblack", 0.8),
    ("floating",     "floating"):    ("fade",      0.8),
}
XFADE_DEFAULT = ("dissolve", 0.8)


def get_transition(out_type: str, in_type: str) -> tuple[str, float]:
    return XFADE_RULES.get((out_type, in_type), XFADE_DEFAULT)


def build_transitions(scenes: list) -> list[tuple[str, float]]:
    ordered = sorted(scenes, key=lambda s: s["order"])
    return [
        get_transition(ordered[i]["component_type"], ordered[i + 1]["component_type"])
        for i in range(len(ordered) - 1)
    ]


TRANSITIONS = build_transitions(SCENES)


def segment_path(scene: dict) -> Path:
    return SEGMENTS_DIR / f"ready_{scene['order']:02d}_{scene['id']}.mp4"


def brand_lint(scenes: list) -> list[str]:
    warnings = []
    banned_in_ids = ("jarvis", "telos", "pai-", "td-keynote")
    for s in scenes:
        low = s["id"].lower()
        for b in banned_in_ids:
            if b in low:
                warnings.append(f"Scene id contains '{b}': {s['id']}")
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
        print("[WARN] Missing segments -- falling back to simple concat.")
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
    concat_file = SEGMENTS_DIR / f"concat_{BRAND['project_slug']}.txt"
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
    print(f"  {BRAND['name']} DEMO -- scene plan  (auto-derived xfade transitions)")
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

    transitions = build_transitions(SCENES)
    print_plan(transitions)

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
