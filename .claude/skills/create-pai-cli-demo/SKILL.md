---
name: create-pai-cli-demo
description: Produce polished CLI/workflow demo MP4 using PAI Remotion component library
---

# IDENTITY and PURPOSE

PAI CLI demo video producer. Generate polished MP4s from scene descriptions using the PAI Remotion component library — no screen recording. Scope: CLI/terminal workflow demos only; new visual primitives require new Remotion components first.

# DISCOVERY

## Stage
BUILD

## Syntax
/create-pai-cli-demo <project-name> [--scenes N] [--type algorithm-loop|custom]

## Parameters
- project-name: slug for the demo (e.g., `crypto-bot`, `pai-workflow`, `jarvis-app`)
- --scenes N: target scene count (default: 8-10 for algorithm-loop)
- --type: demo narrative structure (default: algorithm-loop — 7-phase TheAlgorithm)

## Component Library (PAI Remotion, `remotion/src/scenes/`)
- `FloatingCard` — linen background + dark/white content card; standard scene container
- `ClaudeCliContent` — animated multi-turn Claude CLI conversation simulator
- `ThreePanelScene` — left terminal (52%) + top-right context + bottom-right card; use with `snapFromFull=true` when preceded by a zoomin xfade
- `TerminalContent` — single command + output lines (no conversation)
- `MarkdownPRDContent` — GitHub dark theme .md file with ISC items, sequential reveal
- `FolderViewContent` — macOS-style folder listing with file highlight
- `ChecklistContent` — animated checklist with progress tracking
- `TitleCard` — full-frame title/hook card (dark variants)

**If your demo needs visuals not in this list**: halt at Step 0 with a component gap list. Build the missing component(s) first, then return to this skill.

## Examples
- /create-pai-cli-demo crypto-bot
- /create-pai-cli-demo jarvis-app --type custom --scenes 6
- /create-pai-cli-demo pai-workflow --type algorithm-loop

## Chains
- Before: /architecture-review (validate stack before new demo type), /research (for unfamiliar project domains)
- After: /commit (commit composition file + render script), /learning-capture
- Full: /create-pai-cli-demo > /commit > /learning-capture

## Output Contract
- Input: project name + optional demo type
- Output: `remotion/src/compositions/<project>.tsx` + `tools/scripts/demo_builder/render_<project>.py` + assembled MP4 at `memory/work/<project>/<project>_demo_<date>.mp4`
- Side effects: new composition file registered in Root.tsx

## autonomous_safe
false

# STEPS

## Step 0: COMPONENT INVENTORY CHECK

Before any scene planning, present the component library (see DISCOVERY section) and ask:

> "Which of these components cover your demo's visual needs? If your demo requires something not in this list (e.g., price charts, browser UI, Slack messages, app screenshots), name it now — I'll output a component gap list and we stop here until those are built."

If Eric names a gap: output the list, recommend building missing components via `/implement-prd`, stop.
If all scenes can be covered by existing components: proceed to Step 1.

## Step 1: BRAND CONFIG

Collect and lock before any code generation:

```json
{
  "project_name": "...",     // Display name (e.g., "Crypto Bot")
  "prompt_prefix": "... > ", // CLI prompt (e.g., "crypto > ")
  "project_slug": "...",     // filename slug (e.g., "crypto-bot")
  "output_dir": "memory/work/<slug>/"
}
```

Write to `memory/work/<project-slug>/demo_brand.json`. This is the source of truth — all generated files must reference it, never hardcode brand strings.

## Step 2: SCENE ARC

Do NOT apply algorithm-loop template automatically. Instead:

1. Ask Eric: "Describe what this demo needs to show — what is the one thing the viewer should leave understanding?"
2. Ask: "Walk me through the story in 3-4 sentences: what happens first, what's the pivot, what's the payoff?"
3. Propose a scene list based on Eric's description (NOT a template). For each scene: `order | name | headline | component_type | duration_s | narrative purpose`
4. Wait for Eric to approve/adjust the scene list before proceeding.

If Eric's demo naturally follows TheAlgorithm (observe→plan→build→verify→learn), you may label phases — but derive the scene list from the story, not the other way around.

## Step 3: SCAFFOLD

Once scene arc is approved:

**A. Generate render script** from `render_template.py`:
- Copy to `tools/scripts/demo_builder/render_<project-slug>.py`
- Fill in BRAND config from demo_brand.json
- Fill in SCENES list with approved scene arc
- TRANSITIONS are auto-derived by `build_transitions()` from component_type — do not set manually

**B. Generate composition file** at `remotion/src/compositions/<project-slug>.tsx`:
- Brand constants at the top (from demo_brand.json)
- Stub Composition for each scene with correct id, durationInFrames, component_type
- `snapFromFull={true}` on all ThreePanelScene compositions (required — xfade rules assume it)
- Shared turn data arrays as TypeScript constants above the compositions

**C. Register in Root.tsx**:
- Import `<ProjectCompositions>` from `./compositions/<project-slug>`
- Add `<ProjectCompositions />` inside `RemotionRoot` return fragment

**D. Brand lint** (non-optional): grep composition file and render script for any hardcoded brand string (project name, prompt prefix) that is NOT reading from the brand constants at the top. Fix before proceeding.

## Step 4: CONTENT BUILD

For each scene in scene arc order:
1. Eric describes the scene intent: what CLI commands, what dialogue, what text, what files to show
2. Claude generates the scene JSX inside the composition file
3. Eric reviews (optionally renders single scene: `npx remotion render src/index.ts <scene-id> out.mp4` from `remotion/`)
4. Iterate until approved, then move to next scene

**Timing guidance** (from PAI meta-demo experience):
- Hook/capture scenes: 8-12s
- Dialogue/conversation scenes: 14-24s (more turns = longer)
- ThreePanelScene: 14-22s (give right panel time to reveal)
- Build slack into durations — iteration always makes scenes longer

**Animation conventions** (encode as code, not docs):
- `snapFromFull={true}` — always on ThreePanelScene; auto-derived transition rule (zoomin) depends on it
- `instant: true, pauseAfter: 0` — apply to past-context turns in ThreePanelScene left panel
- `startFrame` — offset from scene start before first animation; ~18-35 frames typical
- `pauseAfter: 90-120` — 1.5-2s read pause between key exchanges in slow-paced scenes

## Step 5: RENDER + ASSEMBLE

Single scene (iteration):
```bash
cd remotion
npx remotion render src/index.ts <scene-id> out/test.mp4
```

All scenes + assemble (Windows — shell=True required for npx):
```bash
python tools/scripts/demo_builder/render_<project-slug>.py --dry-run  # verify plan
python tools/scripts/demo_builder/render_<project-slug>.py --scene N  # single scene
python tools/scripts/demo_builder/render_<project-slug>.py             # all + assemble
python tools/scripts/demo_builder/render_<project-slug>.py --assemble-only  # if segments already rendered
```

Note: `subprocess.run(["npx", ...])` on Windows requires `shell=True` — already baked into render_template.py.

## Step 6: BRAND AUDIT

After first full assembly, run:
```bash
grep -r "jarvis\|Jarvis\|JARVIS" remotion/src/compositions/<project-slug>.tsx
grep -r "jarvis\|Jarvis\|JARVIS" tools/scripts/demo_builder/render_<project-slug>.py
```

Extend grep pattern for any project-specific brand names that should not appear. Fix any hits before declaring done.

# TRANSITION RULES (encoded in render_template.py — reference only)

| Outgoing type | Incoming type | xfade | Duration |
|--------------|---------------|-------|----------|
| floating | three_panel | zoomin | 1.0s |
| three_panel | floating | fadeblack | 0.8s |
| three_panel | three_panel | fadeblack | 0.8s |
| floating | floating | fade | 0.8s |
| (unknown) | (unknown) | dissolve | 0.8s |

`zoomin` → incoming ThreePanelScene **must** have `snapFromFull={true}`.
The Win+Left snap effect: xfade zooms into outgoing terminal → new scene starts full-width → compresses left → right panel fills the gap. Without `snapFromFull`, the terminal appears already at 52% (slideshow, not animation).

# UPGRADE PATH (Phase 6-7: /create-demo-video)

Generalization blockers: (1) new Remotion component types (PriceChartScene, SlackNotificationScene, AppScreenshotScene, BrowserScene); (2) inventory step → routing step; (3) new XFADE_RULES entries; (4) new storyboard templates (product-tour, data-story, incident-review); (5) YAML scene contracts (requires/ensures per scene) enabling per-scene agent parallelism with `model="claude-sonnet-4-6"`.

Real blocker is item 1 (new components), not orchestration. When ready: `/create-demo-video` superskill routes to this skill for CLI demos.

# VERIFY

- `remotion/src/compositions/<project>.tsx` exists with brand constants at top | Verify: Read file, check for BRAND_NAME, BRAND_PROMPT, BRAND_SLUG constants
- `tools/scripts/demo_builder/render_<project>.py` exists with BRAND dict and auto-derived TRANSITIONS | Verify: Read file, grep for `build_transitions(SCENES)`
- Root.tsx registers new composition file | Verify: grep Root.tsx for import of new composition
- Brand audit passed (no hardcoded brand strings) | Verify: Run brand audit grep commands from Step 6
- Final MP4 exists at output path | Verify: `ls memory/work/<project>/`
- No banned brand names in assembled video title/captions (re-watch scene 1 and any text-heavy scenes) | Verify: Manual review

# LEARN

- Track which component types were most often requested but missing from the library — these are the priority candidates for Phase 6-7 component builds
- If scene timing requires > 2 adjustment cycles, note the scene type — timing heuristics need calibration for that component
- If brand audit catches hits after content build, note that the content build phase did not enforce brand constants — tighten the brand lint step
- If Eric's scene arc diverges significantly from the algorithm-loop template, capture the narrative shape as a candidate for a new storyboard template

- Write a signal to memory/learning/signals/{YYYY-MM-DD}_pai-demo-{slug}.md when a demo reveals a new component combination that resonates, or when component library gaps affect 2+ scenes; rating 7+ for library gap signals that become Phase 6-7 build candidates

# INPUT

INPUT:
