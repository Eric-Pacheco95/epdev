"""
render_demo_skill.py — Render and assemble the "How We Built /create-demo-video" meta-demo.

10 scenes, ~2:17 total (with xfade transitions). All Remotion (no VHS).

Scene order (authentic Algorithm loop):
  01  demo-skill-hook-01      Hook — /create-demo-video payoff (8s, 2s hold after reveals)
  02  demo-skill-observe-02   OBSERVE+THINK — back-and-forth with 1.5s read pauses (15s)
  03  demo-skill-arch-03      PLAN — three-panel: arch-review CLI left + verdict bottom-right (22s)
  04  demo-skill-prd-qa-05    PLAN — /create-prd Q&A, starts with user typing (24s)
  05  demo-skill-prd-03       PLAN — ISC checklist locked (16s)
  06  demo-skill-build-07     BUILD — /implement-prd tool calls (13s)
  07  demo-skill-iterate-08   VERIFY — three-panel: build left + iterate feedback right (14s)
  08  demo-skill-folder-view  EXECUTE — Eric opens folder, MP4 highlighted (10s)
  09  demo-skill-output-04    EXECUTE — terminal ls output (13s)
  10  demo-skill-capture-05   LEARN — /create-skill -> skill #48 (12s)

Transitions (xfade filter, 0.8-1.0s):
  01->02  fadeblack  0.8s  — chapter break hook to story
  02->03  zoomin     1.0s  — zoom into CLI -> three-panel snap (Win+Left effect)
  03->04  fade       0.8s  — arch three-panel -> prd Q&A
  04->05  dissolve   0.8s  — Q&A -> ISC checklist
  05->06  fade       0.8s  — checklist -> build CLI
  06->07  zoomin     1.0s  — zoom into CLI -> iterate three-panel snap
  07->08  fadeblack  0.8s  — chapter break to folder view
  08->09  fade       0.8s  — folder -> terminal output
  09->10  dissolve   0.8s  — output -> skill capture

Usage:
    python tools/scripts/demo_builder/render_demo_skill.py
    python tools/scripts/demo_builder/render_demo_skill.py --scene 2
    python tools/scripts/demo_builder/render_demo_skill.py --assemble-only
    python tools/scripts/demo_builder/render_demo_skill.py --dry-run
"""

import argparse
import subprocess
import sys
from pathlib import Path

REPO_ROOT       = Path(__file__).parent.parent.parent.parent.resolve()
REMOTION_DIR    = REPO_ROOT / "remotion"
SEGMENTS_DIR    = REPO_ROOT / "tools/scripts/demo_builder/output/segments"
OUTPUT_PATH     = REPO_ROOT / "memory/work/td-innovation-keynote/jarvis_skill_demo_2026-04-15.mp4"

# ─── Scene manifest ──────────────────────────────────────────────────────────
SCENES = [
    {"order":  1, "id": "demo-skill-hook-01",     "duration_s":  8},  # 8s: 2s hold after reveals
    {"order":  2, "id": "demo-skill-observe-02",  "duration_s": 15},  # 15s: slower + 1.5s read pause
    {"order":  3, "id": "demo-skill-arch-03",     "duration_s": 22},  # 22s: three-panel merged
    {"order":  4, "id": "demo-skill-prd-qa-05",   "duration_s": 24},  # 24s: /create-prd prefix + pauses
    {"order":  5, "id": "demo-skill-prd-03",      "duration_s": 16},
    {"order":  6, "id": "demo-skill-build-07",    "duration_s": 13},
    {"order":  7, "id": "demo-skill-iterate-08",  "duration_s": 14},  # 14s: three-panel
    {"order":  8, "id": "demo-skill-folder-view", "duration_s": 10},
    {"order":  9, "id": "demo-skill-output-04",   "duration_s": 13},
    {"order": 10, "id": "demo-skill-capture-05",  "duration_s": 12},
]

# ─── xfade transition plan ────────────────────────────────────────────────────
# One entry per scene boundary (len = len(SCENES) - 1)
TRANSITIONS = [
    ("fadeblack", 0.8),   # 01->02  hook -> observe  (chapter break)
    ("zoomin",    1.0),   # 02->03  observe -> arch three-panel (zoom into CLI, snaps to left)
    ("fade",      0.8),   # 03->04  arch -> prd Q&A
    ("dissolve",  0.8),   # 04->05  Q&A -> ISC checklist
    ("fade",      0.8),   # 05->06  checklist -> build CLI
    ("zoomin",    1.0),   # 06->07  build -> iterate three-panel (zoom into CLI, snaps to left)
    ("fadeblack", 0.8),   # 07->08  iterate -> folder view  (chapter break)
    ("fade",      0.8),   # 08->09  folder -> terminal output
    ("dissolve",  0.8),   # 09->10  output -> skill capture
]

assert len(TRANSITIONS) == len(SCENES) - 1, "Transition count must equal scene count - 1"


def segment_path(scene: dict) -> Path:
    return SEGMENTS_DIR / f"ready_{scene['order']:02d}_{scene['id']}.mp4"


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
    result = subprocess.run(cmd, cwd=REMOTION_DIR)
    return result.returncode


def build_xfade_filter(scenes: list, transitions: list) -> tuple[str, float]:
    """
    Build an FFmpeg -filter_complex string chaining xfade transitions.
    Returns (filter_string, total_output_duration_s).
    """
    parts = []
    stream_dur = float(scenes[0]["duration_s"])
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
        stream_dur = stream_dur + scenes[i + 1]["duration_s"] - trans_dur
        prev_out = next_out

    return ";".join(parts), stream_dur


def assemble_with_xfade(scenes: list) -> int:
    ordered = sorted(scenes, key=lambda s: s["order"])
    present = [s for s in ordered if segment_path(s).exists()]
    missing = [s for s in ordered if not segment_path(s).exists()]

    if missing:
        print(f"[WARN] Missing: {[s['id'] for s in missing]}")

    if not present:
        print("[ERROR] No segments to assemble.")
        return 1

    # If some scenes are missing, fall back to simple concat
    if missing:
        print("[WARN] Missing segments — falling back to simple concat (no xfade).")
        return _simple_concat(present)

    # Build input args
    inputs = []
    for s in ordered:
        inputs.extend(["-i", str(segment_path(s))])

    filter_str, total_dur = build_xfade_filter(ordered, TRANSITIONS)

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


def print_plan():
    print("\n" + "=" * 72)
    print("  DEMO SKILL VIDEO — scene plan  (xfade transitions)")
    print(f"  Scenes: {len(SCENES)}   Transitions: {len(TRANSITIONS)}")
    print("=" * 72)
    t = 0.0
    total_transition_s = sum(d for _, d in TRANSITIONS)
    print(f"  Raw total: {sum(s['duration_s'] for s in SCENES)}s  |  "
          f"Transition overlap: {total_transition_s:.1f}s  |  "
          f"Output: ~{sum(s['duration_s'] for s in SCENES) - total_transition_s:.0f}s")
    print("-" * 72)
    for i, s in enumerate(SCENES):
        end = t + s["duration_s"]
        m0, s0 = divmod(int(t), 60)
        m1, s1 = divmod(int(end), 60)
        trans = f"  -> {TRANSITIONS[i][0]} {TRANSITIONS[i][1]:.1f}s" if i < len(TRANSITIONS) else ""
        print(f"  {s['order']:2d}  {m0}:{s0:02d}–{m1}:{s1:02d}  ({s['duration_s']:2d}s)  {s['id']}{trans}")
        t = end
    print("=" * 72 + "\n")


def main():
    parser = argparse.ArgumentParser(description="Render demo-skill video")
    parser.add_argument("--scene",        type=int,         help="Render single scene by order number")
    parser.add_argument("--assemble-only", action="store_true", help="Skip rendering, only assemble")
    parser.add_argument("--dry-run",       action="store_true", help="Print plan only")
    args = parser.parse_args()

    print_plan()
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
        for scene in SCENES:
            rc = render_scene(scene)
            if rc != 0:
                failed.append(scene["id"])
        if failed:
            print(f"\n[WARN] {len(failed)} scene(s) failed: {failed}")

    rc = assemble_with_xfade(SCENES)
    if rc == 0 and OUTPUT_PATH.exists():
        size_mb = OUTPUT_PATH.stat().st_size / (1024 * 1024)
        print(f"\n[DONE] {OUTPUT_PATH}")
        print(f"       {size_mb:.1f} MB")
        print(f"       start \"{OUTPUT_PATH}\"")
    else:
        print("[ERROR] Assembly failed.")
        sys.exit(1)


if __name__ == "__main__":
    sys.path.insert(0, str(Path(__file__).parent))
    main()
