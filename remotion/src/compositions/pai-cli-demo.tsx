/**
 * pai-cli-demo.tsx — PAI "create-demo-video" meta-demo compositions.
 *
 * 10-scene authentic Algorithm loop:
 *   01 hook-01       Hook — /create-demo-video payoff (8s)
 *   02 observe-02    OBSERVE+THINK — back-and-forth dialogue (15s)
 *   03 arch-03       PLAN — /architecture-review three-panel (22s)  [snapFromFull]
 *   04 prd-qa-05     PLAN — /create-prd Q&A (24s)
 *   05 prd-03        PLAN — ISC checklist markdown PRD (16s)
 *   06 build-07      BUILD — /implement-prd tool calls (13s)
 *   07 iterate-08    VERIFY — three-panel iterate feedback (14s)    [snapFromFull]
 *   08 folder-view   EXECUTE — folder view, MP4 highlighted (10s)
 *   09 output-04     EXECUTE — terminal ls output (13s)
 *   10 capture-05    LEARN — /create-skill → skill #48 (12s)
 *
 * snapFromFull: scenes 03 + 07 start at 100% left-panel width and compress
 * to 52% in sync with the right-panel slide-in, creating the Win+Left arrow
 * snap effect. Required whenever a zoomin xfade precedes a ThreePanelScene.
 *
 * Brand: PAI (Personal AI Infrastructure). Prompt prefix: "pai > ".
 * To create a new demo with different brand: copy this file, update brand
 * constants, and register in Root.tsx as a new project composition.
 */

import React from "react";
import { Composition } from "remotion";
import { FloatingCard, LINEN, CARD_DARK, CARD_WHITE } from "../scenes/FloatingCard";
import { TerminalContent } from "../scenes/TerminalContent";
import { ClaudeCliContent, ChatTurn } from "../scenes/ClaudeCliContent";
import { ThreePanelScene } from "../scenes/ThreePanelScene";
import { FolderViewContent } from "../scenes/FolderViewContent";
import { MarkdownPRDContent } from "../scenes/MarkdownPRDContent";
import { FPS, WIDTH, HEIGHT } from "../config";

// ─── Brand config ────────────────────────────────────────────────────────────
// Change these for a new demo project. All scenes derive brand from here.
const BRAND_NAME    = "PAI";
const BRAND_PROMPT  = "pai > ";
const BRAND_SLUG    = "create-demo-video";
const SKILL_NUMBER  = 48;

// ─── Shared turn data ────────────────────────────────────────────────────────

/** Scene 2: observe/think dialogue. Also used as instant past context in scene 3. */
const OBSERVE_TURNS: ChatTurn[] = [
  {
    role: "user",
    text: "Innovation week: can we build a skill that creates demo videos from a prompt? No screen recording.",
  },
  {
    role: "assistant",
    lines: [
      "Yes — Claude's videos are programmatic composition, not recordings.",
      "Terminal = VHS rendered output. Browser = React mock, composited frame-by-frame.",
      "We can build this. Validating the stack before committing.",
    ],
    toolCalls: [
      { tool: "Agent", target: "/architecture-review + /research demo-video-generation" },
    ],
    pauseAfter: 90,
  },
  {
    role: "user",
    text: "What about MoviePy? I've seen others use it for video work.",
  },
  {
    role: "assistant",
    lines: [
      "MoviePy 2.x breaks 1.x API — already flagged for exclusion.",
      "FFmpeg alone is sufficient for assembly. Arch review will confirm.",
    ],
  },
];

/** Architecture review dialogue — used in scene 3 left terminal (animated below observe context). */
const ARCH_REVIEW_TURNS: ChatTurn[] = [
  {
    role: "user",
    text: "run this through /architecture-review first",
  },
  {
    role: "assistant",
    lines: [
      "Running arch review + research in parallel...",
      "VHS on Windows: BROKEN (#631, #721) — Docker path confirmed stable",
      "MoviePy 2.x breaks 1.x API — excluded from stack",
      "FFmpeg alone is sufficient for segment assembly",
      "Verdict: Build it. Stack validated. Ship Phase 1 today.",
    ],
    toolCalls: [
      { tool: "Agent", target: "first-principles analysis" },
      { tool: "Agent", target: "fallacy detection + red-team" },
    ],
  },
];

/** Build CLI dialogue — used as instant past context in scene 7. */
const BUILD_TURNS: ChatTurn[] = [
  {
    role: "user",
    text: "/implement-prd memory/work/create-demo-video/PRD.md",
  },
  {
    role: "assistant",
    lines: [
      "ISC quality gate: PASS (6/6). Building Phase 1...",
      "5 scenes rendering in parallel -> segments assembled",
    ],
    toolCalls: [
      { tool: "Read",  target: "memory/work/create-demo-video/PRD.md" },
      { tool: "Write", target: "src/scenes/FloatingCard.tsx" },
      { tool: "Write", target: "src/scenes/TerminalContent.tsx" },
      { tool: "Write", target: "src/scenes/ChecklistContent.tsx" },
      { tool: "Bash",  target: "npx remotion render --parallel 5" },
    ],
  },
];

// ─── Arch review verdict card (scene 3 bottom-right) ─────────────────────────
const ARCH_ROWS = [
  { tool: "VHS Docker",  status: "adopt",  note: "Terminal -> MP4, proven on Linux" },
  { tool: "Remotion",    status: "adopt",  note: "React -> MP4, native Windows" },
  { tool: "FFmpeg",      status: "adopt",  note: "Segment assembly + audio mix" },
  { tool: "MoviePy",     status: "reject", note: "2.x breaks 1.x — excluded" },
];

const ArchReviewCard: React.FC = () => (
  <div style={{ fontFamily: "system-ui, -apple-system, sans-serif" }}>
    {ARCH_ROWS.map(({ tool, status, note }) => (
      <div
        key={tool}
        style={{
          display: "flex",
          alignItems: "center",
          gap: 18,
          padding: "12px 0",
          borderBottom: "1px solid #F3F4F6",
        }}
      >
        <span style={{ fontSize: 20, fontWeight: 700, color: status === "adopt" ? "#16A34A" : "#DC2626", width: 24, flexShrink: 0 }}>
          {status === "adopt" ? "✓" : "✗"}
        </span>
        <span style={{ fontSize: 19, fontWeight: 600, color: "#1A1917", width: 180, flexShrink: 0 }}>{tool}</span>
        <span style={{ fontSize: 17, color: "#6B7280" }}>{note}</span>
      </div>
    ))}
    <div style={{
      marginTop: 22,
      padding: "14px 20px",
      backgroundColor: "#F0FDF4",
      borderRadius: 10,
      borderLeft: "4px solid #16A34A",
      fontFamily: "Georgia, serif",
      fontSize: 19,
      fontWeight: 700,
      color: "#14532D",
    }}>
      Verdict: Build it. Stack validated. Ship Phase 1 today.
    </div>
  </div>
);

// ─── Compositions ─────────────────────────────────────────────────────────────

export const PAICliDemoCompositions: React.FC = () => (
  <>
    {/* Scene 01: Hook — 8s */}
    <Composition
      id="demo-skill-hook-01"
      component={() => (
        <FloatingCard
          bg={LINEN}
          cardBg={CARD_DARK}
          headline={"What if your workflow could\nbuild its own demo?"}
          subheadline="Let me show you how we built this skill"
          enterAt={0}
        >
          <TerminalContent
            prompt={BRAND_PROMPT}
            command={`/create-demo-video "TD Innovation 2026" --style cinematic`}
            outputLines={[
              { text: "✓  Reading keynote scenes from memory/work/td-innovation-keynote/", color: "#A3E635" },
              { text: "✓  VHS tape rendered  ->  terminal_02.mp4", color: "#A3E635" },
              { text: "✓  Remotion compositions compiled  ->  5 scenes", color: "#A3E635" },
              { text: `✓  FFmpeg assembly complete  ->  pai_demo_2026-04-15.mp4`, color: "#6EE7B7", bold: true },
            ]}
            startFrame={18}
            typingSpeed={0.7}
            lineDelay={22}
          />
        </FloatingCard>
      )}
      durationInFrames={8 * FPS}
      fps={FPS}
      width={WIDTH}
      height={HEIGHT}
      defaultProps={{}}
    />

    {/* Scene 02: OBSERVE+THINK — 15s, 1.5s pause between exchanges */}
    <Composition
      id="demo-skill-observe-02"
      component={() => (
        <FloatingCard
          bg={LINEN}
          cardBg={CARD_DARK}
          headline={"It starts with a question."}
          subheadline="No screen recording needed — we build it programmatically"
          enterAt={0}
        >
          <ClaudeCliContent
            phase="OBSERVE · THINK"
            startFrame={25}
            userTypingSpeed={1.5}
            assistantLineDelay={22}
            toolCallDelay={14}
            turnGap={30}
            turns={OBSERVE_TURNS}
          />
        </FloatingCard>
      )}
      durationInFrames={15 * FPS}
      fps={FPS}
      width={WIDTH}
      height={HEIGHT}
      defaultProps={{}}
    />

    {/*
      Scene 03: PLAN — /architecture-review three-panel.
      snapFromFull=true: left panel starts at 100% width, compresses to 52% in sync
      with right-panel slide-in (Win+Left arrow effect). Required because a zoomin
      xfade precedes this scene.
    */}
    <Composition
      id="demo-skill-arch-03"
      component={() => (
        <ThreePanelScene
          phaseLabel="PLAN · Architecture Review"
          headline={"Should we even\nbuild this?"}
          subheadline="/architecture-review — validate the stack before writing a single line"
          leftContent={
            <ClaudeCliContent
              phase="OBSERVE · THINK → PLAN"
              startFrame={15}
              userTypingSpeed={2.2}
              assistantLineDelay={20}
              toolCallDelay={13}
              turnGap={18}
              turns={[
                ...OBSERVE_TURNS.map(t => ({ ...t, instant: true, pauseAfter: 0 })),
                ...ARCH_REVIEW_TURNS,
              ]}
            />
          }
          bottomContent={<ArchReviewCard />}
          bottomCardBg={CARD_WHITE}
          bottomRevealFrame={320}
          leftWidthPct={52}
          leftDim={1.0}
          snapFromFull={true}
        />
      )}
      durationInFrames={22 * FPS}
      fps={FPS}
      width={WIDTH}
      height={HEIGHT}
      defaultProps={{}}
    />

    {/* Scene 04: PLAN — /create-prd Q&A, 24s */}
    <Composition
      id="demo-skill-prd-qa-05"
      component={() => (
        <FloatingCard
          bg={LINEN}
          cardBg={CARD_DARK}
          headline={"Requirements before code.\nAlways."}
          subheadline={`/create-prd — ${BRAND_NAME} asks questions, you drive the design`}
          enterAt={0}
        >
          <ClaudeCliContent
            phase="PLAN"
            startFrame={25}
            userTypingSpeed={1.5}
            assistantLineDelay={22}
            toolCallDelay={14}
            turnGap={28}
            turns={[
              {
                role: "user",
                text: `/create-prd ${BRAND_SLUG} skill`,
                pauseAfter: 20,
              },
              {
                role: "assistant",
                lines: [
                  "Before generating — 3 questions to surface assumptions:",
                  "1. Quality bar: Pillow static frames or Remotion animated renders?",
                  "2. Should the skill propose a scene plan for you to review first?",
                  "3. Audio narration for Phase 1?",
                ],
                pauseAfter: 120,
              },
              {
                role: "user",
                text: "Remotion renders — matching Claude Code quality. Yes, I review the plan. No audio for P1.",
                pauseAfter: 120,
              },
              {
                role: "assistant",
                lines: [
                  "Last one: scope — TD keynote only, or design for reuse across projects?",
                ],
                pauseAfter: 120,
              },
              {
                role: "user",
                text: "PAI project for P1 — but design for reuse. Should work for other project demos too.",
              },
            ]}
          />
        </FloatingCard>
      )}
      durationInFrames={24 * FPS}
      fps={FPS}
      width={WIDTH}
      height={HEIGHT}
      defaultProps={{}}
    />

    {/* Scene 05: PLAN — ISC checklist as markdown PRD, 16s */}
    <Composition
      id="demo-skill-prd-03"
      component={() => (
        <FloatingCard
          bg={LINEN}
          cardBg="#0D1117"
          headline={"Requirements first.\nThen code."}
          subheadline="/create-prd — markdown PRD with ISC criteria, quality gate enforced"
          enterAt={0}
        >
          <MarkdownPRDContent
            startFrame={20}
            itemDelay={24}
            title={BRAND_SLUG}
            phase="Phase 1 — MVP"
            items={[
              { text: "VHS Docker renders terminal scenes to MP4",    tag: "P1-1" },
              { text: "Remotion compiles title + UI mockup scenes",   tag: "P1-2" },
              { text: "FFmpeg assembles segments with fade cuts",      tag: "P1-3" },
              { text: "Video plays without exposing personal data",    tag: "P1-4" },
              { text: "Full demo video under 3 minutes",              tag: "P1-5" },
            ]}
          />
        </FloatingCard>
      )}
      durationInFrames={16 * FPS}
      fps={FPS}
      width={WIDTH}
      height={HEIGHT}
      defaultProps={{}}
    />

    {/* Scene 06: BUILD — /implement-prd tool calls, 13s */}
    <Composition
      id="demo-skill-build-07"
      component={() => (
        <FloatingCard
          bg={LINEN}
          cardBg={CARD_DARK}
          headline={"Then we build."}
          subheadline="/implement-prd — ISC items verified one by one"
          enterAt={0}
        >
          <ClaudeCliContent
            phase="BUILD"
            startFrame={35}
            userTypingSpeed={2.5}
            assistantLineDelay={16}
            toolCallDelay={11}
            turnGap={22}
            turns={BUILD_TURNS}
          />
        </FloatingCard>
      )}
      durationInFrames={13 * FPS}
      fps={FPS}
      width={WIDTH}
      height={HEIGHT}
      defaultProps={{}}
    />

    {/*
      Scene 07: VERIFY — iterate three-panel.
      snapFromFull=true: same Win+Left snap effect as scene 03.
      Required because a zoomin xfade precedes this scene.
    */}
    <Composition
      id="demo-skill-iterate-08"
      component={() => (
        <ThreePanelScene
          phaseLabel="VERIFY · Iterate"
          headline={"Iterate until right."}
          subheadline="VERIFY loop — feedback drives every re-render"
          leftContent={
            <ClaudeCliContent
              phase="BUILD → VERIFY"
              startFrame={15}
              userTypingSpeed={1.8}
              assistantLineDelay={20}
              toolCallDelay={13}
              turnGap={22}
              turns={[
                ...BUILD_TURNS.map(t => ({ ...t, instant: true, pauseAfter: 0 })),
                {
                  role: "user",
                  text: "text too fast. zoom shouldn't be on hook — zoom is for showcasing outputs.",
                  pauseAfter: 80,
                },
                {
                  role: "assistant",
                  lines: [
                    "Good catches — fixing both:",
                  ],
                  toolCalls: [
                    { tool: "Edit", target: "Root.tsx — hook lineDelay 6->22 frames" },
                    { tool: "Edit", target: "Root.tsx — hook holdZoom 1.12->1.0 (flat hold)" },
                    { tool: "Edit", target: "FloatingCard.tsx — fade-out 0.35s->0.8s" },
                    { tool: "Bash",  target: "npx remotion render (5 scenes) + ffmpeg concat" },
                  ],
                },
              ]}
            />
          }
          leftWidthPct={52}
          leftDim={1.0}
          snapFromFull={true}
        />
      )}
      durationInFrames={14 * FPS}
      fps={FPS}
      width={WIDTH}
      height={HEIGHT}
      defaultProps={{}}
    />

    {/* Scene 08: EXECUTE — folder view, MP4 highlighted, 10s */}
    <Composition
      id="demo-skill-folder-view"
      component={() => (
        <FloatingCard
          bg={LINEN}
          cardBg={CARD_WHITE}
          headline={"It rendered."}
          subheadline="Prompt -> polished MP4 — no screen recording, no manual editing"
          enterAt={0}
        >
          <FolderViewContent
            folderPath="memory/work/td-innovation-keynote/"
            startFrame={30}
            fileDelay={22}
            highlightDelay={20}
            files={[
              { name: "keynote_2026-04-15.md",            type: "md",  size: "28 KB" },
              { name: "scene_definitions.py",              type: "py",  size: "4.1 KB" },
              { name: "pai_skill_demo_2026-04-15.mp4", type: "mp4", size: "21.6 MB", duration: "2:26", highlight: true },
            ]}
          />
        </FloatingCard>
      )}
      durationInFrames={10 * FPS}
      fps={FPS}
      width={WIDTH}
      height={HEIGHT}
      defaultProps={{}}
    />

    {/* Scene 09: EXECUTE — terminal ls output, 13s */}
    <Composition
      id="demo-skill-output-04"
      component={() => (
        <FloatingCard
          bg={LINEN}
          cardBg={CARD_DARK}
          headline={"The output:"}
          subheadline="Prompt -> polished MP4. No screen recording."
          enterAt={0}
        >
          <TerminalContent
            prompt={BRAND_PROMPT}
            command="ls -lh memory/work/td-innovation-keynote/"
            outputLines={[
              { text: "pai_demo_2026-04-15.mp4    2.9 MB    1:52", color: "#6EE7B7", bold: true },
              { text: "", color: "#4B5563" },
              { text: "5 scenes assembled:", color: "#9CA3AF" },
              { text: "  terminal_02.mp4   workflow-engine deep-analysis", color: "#A3E635", indent: 1 },
              { text: "  title_01.mp4      hook card", color: "#A3E635", indent: 1 },
              { text: "  ui_04.mp4         Claude.ai PIPEDA demo", color: "#A3E635", indent: 1 },
            ]}
            startFrame={20}
            typingSpeed={1.2}
            lineDelay={20}
          />
        </FloatingCard>
      )}
      durationInFrames={13 * FPS}
      fps={FPS}
      width={WIDTH}
      height={HEIGHT}
      defaultProps={{}}
    />

    {/* Scene 10: LEARN — /create-skill -> skill #48, 12s */}
    <Composition
      id="demo-skill-capture-05"
      component={() => (
        <FloatingCard
          bg={LINEN}
          cardBg={CARD_DARK}
          headline={"Validated once.\nSkill forever."}
          subheadline={`The workflow that built this video is now skill #${SKILL_NUMBER}`}
          enterAt={0}
        >
          <TerminalContent
            prompt={BRAND_PROMPT}
            command={`/create-skill ${BRAND_SLUG}`}
            outputLines={[
              { text: `✓  Skill definition written  ->  .claude/skills/${BRAND_SLUG}/SKILL.md`, color: "#A3E635" },
              { text: "✓  Registered in skill registry", color: "#A3E635" },
              { text: "✓  Discoverable via /pai-help", color: "#A3E635" },
              { text: "", color: "#4B5563" },
              { text: `  Skill #${SKILL_NUMBER} active.  Next run: one command.`, color: "#6EE7B7", bold: true },
            ]}
            startFrame={20}
            typingSpeed={0.9}
            lineDelay={20}
          />
        </FloatingCard>
      )}
      durationInFrames={12 * FPS}
      fps={FPS}
      width={WIDTH}
      height={HEIGHT}
      defaultProps={{}}
    />
  </>
);
