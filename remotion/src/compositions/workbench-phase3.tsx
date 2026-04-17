/**
 * workbench-phase3.tsx — Claude Workbench enterprise AI-OS demo compositions.
 *
 * 7-scene, 43s demo reframing the enterprise harness as an "AI Operating System"
 * for regulated banking teams. Shows how /extract-harness --enterprise delivers
 * one surface that captures BOTH complex multi-step work AND high-frequency
 * trivial work — freeing up user time while staying audit-ready.
 *
 *   01 hook        TitleCard          — "AI, as an Operating System." (4s)
 *   02 problem     FloatingCard+CLI   — Two kinds of work eat the day (6s)
 *   03 invoke      FloatingCard+Term  — /extract-harness --enterprise (5s)
 *   04 os          ThreePanelScene    — Skills. Audit. Guards. (9s) [snapFromFull]
 *   05 complex     FloatingCard+MD    — Complex work, captured once (6s)
 *   06 trivial     ThreePanelScene    — Trivial work, automated (8s) [snapFromFull]
 *   07 output      FloatingCard+MD    — /standup-brief actual output (6s)
 *   08 close       TitleCard          — 41 skills. Audit-ready. (5s)
 *
 * Brand: Claude Workbench. Prompt: "workbench > ".
 * Source of truth for brand constants: memory/work/workbench-phase3/demo_brand.json
 */

import React from "react";
import { Composition, interpolate, spring, useCurrentFrame, useVideoConfig } from "remotion";
import { FloatingCard, LINEN, CARD_DARK, CARD_WHITE } from "../scenes/FloatingCard";
import { ClaudeCliContent, ChatTurn } from "../scenes/ClaudeCliContent";
import { ThreePanelScene } from "../scenes/ThreePanelScene";
import { TerminalContent } from "../scenes/TerminalContent";
import { MarkdownPRDContent } from "../scenes/MarkdownPRDContent";
import { TitleCard } from "../scenes/TitleCard";
import { FPS, WIDTH, HEIGHT } from "../config";

// ─── Brand config ────────────────────────────────────────────────────────────
const BRAND_NAME   = "Claude Workbench";
const BRAND_PROMPT = "workbench > ";
const SKILL_AFTER  = 41;

// ─── Shared turns ────────────────────────────────────────────────────────────

/** Scene 2: two kinds of work problem statement. */
const TWO_KINDS_TURNS: ChatTurn[] = [
  {
    role: "user",
    text: "architecture review: payments ingestion redesign",
    pauseAfter: 18,
  },
  {
    role: "assistant",
    lines: [
      "Multi-step: OBSERVE → THINK → PLAN → BUILD → VERIFY.",
      "High-effort. High-value. Usually uncaptured.",
    ],
    pauseAfter: 24,
  },
  {
    role: "user",
    text: "draft standup + tomorrow's AC spec + release notes",
    pauseAfter: 18,
  },
  {
    role: "assistant",
    lines: [
      "Trivial. Daily. Repeats forever.",
      "Also uncaptured. Tribal knowledge walks out the door.",
    ],
  },
];

/** Scene 4: extract-harness producing the OS. */
const OS_BUILD_TURNS: ChatTurn[] = [
  {
    role: "user",
    text: "/extract-harness --enterprise --target claude-workbench",
    pauseAfter: 14,
  },
  {
    role: "assistant",
    lines: [
      "Auditing source skills... 41 KEEP · 15 STRIP · 4 ADAPT",
      "Stripping personal-system refs. Adapting paths.",
      "Writing templates, knowledge, security, history...",
    ],
    toolCalls: [
      { tool: "Write", target: "CLAUDE.md" },
      { tool: "Write", target: ".claude/skills/ (41 skills)" },
      { tool: "Write", target: "security/constitutional-rules.md" },
      { tool: "Write", target: "templates/ + knowledge/ + history/" },
      { tool: "Write", target: ".githooks/pre-commit (PII guard)" },
    ],
  },
];

/** Scene 6: standup-brief running, other daily skills queued. */
const TRIVIAL_AUTOMATION_TURNS: ChatTurn[] = [
  {
    role: "user",
    text: "/standup-brief",
    pauseAfter: 16,
  },
  {
    role: "assistant",
    lines: [
      "Pulling git log + Jira + yesterday's notes...",
      "Y: 3 PRs merged  ·  T: payments schema  ·  Blockers: none",
    ],
    pauseAfter: 18,
  },
  {
    role: "user",
    text: "/acceptance-criteria PAY-4821",
    pauseAfter: 14,
  },
  {
    role: "assistant",
    lines: [
      "Gherkin: 3 happy + 2 edge + 1 NFR. DoR gate: PASS.",
    ],
  },
];

// ─── Enterprise guarantees card (scene 4 bottom-right) ───────────────────────
const GUARANTEE_ROWS = [
  { label: "PII pre-commit hook",     value: "hard-block",    ok: true },
  { label: "Constitutional rules",    value: "layers 1-4",    ok: true },
  { label: "Autonomous agents",       value: "none",          ok: true },
  { label: "Audit trail",             value: "git-sourced",   ok: true },
  { label: "Personal data",           value: "0 matches",     ok: true },
];

const GuaranteesCard: React.FC = () => (
  <div style={{ fontFamily: "system-ui, -apple-system, sans-serif" }}>
    <div style={{ fontSize: 17, fontWeight: 600, color: "#6B7280", marginBottom: 14, letterSpacing: 1.2 }}>
      ENTERPRISE GUARANTEES
    </div>
    {GUARANTEE_ROWS.map(({ label, value, ok }) => (
      <div
        key={label}
        style={{
          display: "flex",
          alignItems: "center",
          gap: 14,
          padding: "9px 0",
          borderBottom: "1px solid #F3F4F6",
        }}
      >
        <span style={{ fontSize: 20, fontWeight: 700, color: ok ? "#16A34A" : "#DC2626", width: 24 }}>
          ✓
        </span>
        <span style={{ fontSize: 17, fontWeight: 600, color: "#1A1917", flex: 1 }}>{label}</span>
        <span style={{ fontSize: 17, fontWeight: 700, color: "#065F46" }}>{value}</span>
      </div>
    ))}
  </div>
);

// ─── Daily-rituals card (scene 6 bottom-right) ───────────────────────────────
const RITUAL_SKILLS = [
  "/standup-brief",
  "/acceptance-criteria",
  "/release-notes",
  "/definition-of-ready",
  "/meeting-to-actions",
  "/retro-facilitator",
];

const RitualsCard: React.FC = () => (
  <div style={{ fontFamily: "system-ui, -apple-system, sans-serif" }}>
    <div style={{ fontSize: 17, fontWeight: 600, color: "#6B7280", marginBottom: 14, letterSpacing: 1.2 }}>
      DAILY RITUALS · AUTOMATED
    </div>
    <div style={{
      display: "grid",
      gridTemplateColumns: "1fr 1fr",
      gap: "10px 18px",
      marginBottom: 18,
    }}>
      {RITUAL_SKILLS.map((s) => (
        <div key={s} style={{
          fontFamily: "'Menlo', 'Monaco', monospace",
          fontSize: 17,
          fontWeight: 600,
          color: "#1A1917",
          padding: "6px 12px",
          backgroundColor: "#F3F4F6",
          borderRadius: 6,
          borderLeft: "3px solid #16A34A",
        }}>
          {s}
        </div>
      ))}
    </div>
    <div style={{
      padding: "14px 18px",
      backgroundColor: "#F0FDF4",
      borderRadius: 10,
      borderLeft: "4px solid #16A34A",
    }}>
      <div style={{ fontSize: 22, fontWeight: 800, color: "#14532D" }}>
        ~6 hrs / week saved
      </div>
      <div style={{ fontSize: 14, color: "#166534", marginTop: 2 }}>
        per delivery team member
      </div>
    </div>
  </div>
);

// ─── Standup brief document content (scene 7) ───────────────────────────────
// Styled as a produced Word-document-esque page, not a SKILL.md preview.
// Sections reveal sequentially: header (f0) → Yesterday (f14) → Today (f48)
// → Blockers (f82) → footer (f110).

interface StandupRow {
  ticket?: string;
  text: string;
}

const STANDUP_YESTERDAY: StandupRow[] = [
  { ticket: "PAY-4821", text: "Shipped payments schema migration — 3 tests green, deployed to UAT" },
  { ticket: "PAY-4798", text: "Reviewed + merged PR: retry backoff on ingestion worker" },
  { ticket: "PAY-4810", text: "Reviewed + merged PR: fraud-rule audit log enrichment" },
  { ticket: "PAY-4830", text: "Drafted AC for fraud-rule engine kickoff (6 Gherkin scenarios)" },
];

const STANDUP_TODAY: StandupRow[] = [
  { ticket: "PAY-4835", text: "Pair on ingestion retry logic — idempotency key rollout (AM)" },
  { ticket: "PAY-4830", text: "DoR gate + refinement prep for sprint kickoff (PM)" },
  { text: "1:1 with RM on Q3 compliance checklist (30 min)" },
];

const SectionHeading: React.FC<{ label: string; color: string; revealFrame: number }> = ({
  label, color, revealFrame,
}) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const progress = spring({ frame: frame - revealFrame, fps, config: { damping: 18, stiffness: 110 }});
  const y = interpolate(progress, [0, 1], [14, 0]);
  const op = interpolate(progress, [0, 1], [0, 1]);
  return (
    <div style={{
      fontFamily: "Georgia, 'Times New Roman', serif",
      fontSize: 26,
      fontWeight: 700,
      color,
      marginBottom: 10,
      marginTop: 4,
      opacity: op,
      transform: `translateY(${y}px)`,
      paddingBottom: 6,
      borderBottom: `2px solid ${color}`,
    }}>
      {label}
    </div>
  );
};

const StandupRowItem: React.FC<{ row: StandupRow; revealFrame: number; badgeColor: string }> = ({
  row, revealFrame, badgeColor,
}) => {
  const frame = useCurrentFrame();
  const op = interpolate(frame, [revealFrame, revealFrame + 8], [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });
  const x = interpolate(frame, [revealFrame, revealFrame + 10], [-8, 0], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });
  return (
    <div style={{
      display: "flex",
      alignItems: "flex-start",
      gap: 12,
      padding: "7px 0",
      opacity: op,
      transform: `translateX(${x}px)`,
    }}>
      <span style={{ fontSize: 18, color: "#6B7280", marginTop: 2 }}>•</span>
      {row.ticket && (
        <span style={{
          display: "inline-block",
          fontFamily: "'Menlo', 'Monaco', monospace",
          fontSize: 14,
          fontWeight: 700,
          color: badgeColor,
          backgroundColor: `${badgeColor}1A`,
          padding: "3px 9px",
          borderRadius: 4,
          marginTop: 1,
          flexShrink: 0,
        }}>
          {row.ticket}
        </span>
      )}
      <span style={{
        fontFamily: "'Inter', system-ui, -apple-system, sans-serif",
        fontSize: 18,
        color: "#1F2937",
        lineHeight: 1.45,
        flex: 1,
      }}>
        {row.text}
      </span>
    </div>
  );
};

const StandupDocContent: React.FC = () => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  // Document header springs in
  const headerProgress = spring({ frame, fps, config: { damping: 20, stiffness: 120 }});
  const headerOp = interpolate(headerProgress, [0, 1], [0, 1]);

  // Footer reveal late
  const footerOp = interpolate(frame, [110, 122], [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });

  const Y_START = 22;
  const T_START = 22 + STANDUP_YESTERDAY.length * 8 + 48;
  const B_START = T_START + STANDUP_TODAY.length * 8 + 40;

  return (
    <div style={{
      backgroundColor: "#FFFFFF",
      borderRadius: 6,
      padding: "32px 44px",
      fontFamily: "'Inter', system-ui, -apple-system, sans-serif",
      boxShadow: "0 0 0 1px #E5E7EB, 0 4px 16px rgba(0,0,0,0.04)",
      minHeight: 560,
    }}>
      {/* Document header */}
      <div style={{ opacity: headerOp, marginBottom: 22 }}>
        <div style={{
          fontFamily: "Georgia, 'Times New Roman', serif",
          fontSize: 30,
          fontWeight: 700,
          color: "#0F172A",
          marginBottom: 4,
        }}>
          Daily Standup
        </div>
        <div style={{
          display: "flex",
          gap: 18,
          fontSize: 14,
          color: "#6B7280",
          paddingBottom: 14,
          borderBottom: "1px solid #E5E7EB",
        }}>
          <span><strong style={{ color: "#374151" }}>Date:</strong>  2026-04-16</span>
          <span><strong style={{ color: "#374151" }}>Sprint:</strong> 24</span>
          <span><strong style={{ color: "#374151" }}>Team:</strong>  Payments Platform</span>
          <span><strong style={{ color: "#374151" }}>Author:</strong> eric.p</span>
        </div>
      </div>

      {/* Yesterday */}
      <SectionHeading label="Yesterday" color="#0EA5E9" revealFrame={14} />
      <div style={{ marginBottom: 20 }}>
        {STANDUP_YESTERDAY.map((row, i) => (
          <StandupRowItem key={i} row={row} revealFrame={Y_START + i * 8} badgeColor="#0EA5E9" />
        ))}
      </div>

      {/* Today */}
      <SectionHeading label="Today" color="#6366F1" revealFrame={48} />
      <div style={{ marginBottom: 20 }}>
        {STANDUP_TODAY.map((row, i) => (
          <StandupRowItem key={i} row={row} revealFrame={T_START + i * 8} badgeColor="#6366F1" />
        ))}
      </div>

      {/* Blockers */}
      <SectionHeading label="Blockers" color="#16A34A" revealFrame={82} />
      <div style={{
        display: "flex",
        alignItems: "center",
        gap: 12,
        padding: "10px 14px",
        backgroundColor: "#F0FDF4",
        borderRadius: 6,
        borderLeft: "4px solid #16A34A",
        opacity: interpolate(frame, [B_START, B_START + 10], [0, 1], {
          extrapolateLeft: "clamp",
          extrapolateRight: "clamp",
        }),
      }}>
        <span style={{ fontSize: 22, color: "#16A34A", fontWeight: 700 }}>✓</span>
        <span style={{ fontSize: 18, color: "#14532D", fontWeight: 600 }}>
          None — unblocked
        </span>
      </div>

      {/* Footer */}
      <div style={{
        marginTop: 28,
        paddingTop: 14,
        borderTop: "1px solid #E5E7EB",
        display: "flex",
        justifyContent: "space-between",
        fontSize: 13,
        color: "#9CA3AF",
        opacity: footerOp,
      }}>
        <span>Generated by <code style={{ color: "#4338CA", fontFamily: "'Menlo', monospace" }}>/standup-brief</code> · git log + Jira + notes</span>
        <span>2.4s · standup_2026-04-16.md</span>
      </div>
    </div>
  );
};

// ─── Compositions ─────────────────────────────────────────────────────────────

export const WorkbenchPhase3Compositions: React.FC = () => (
  <>
    {/* Scene 01: Hook TitleCard — 4s */}
    <Composition
      id="wb3-hook-01"
      component={TitleCard as any}
      durationInFrames={4 * FPS}
      fps={FPS}
      width={WIDTH}
      height={HEIGHT}
      defaultProps={{
        headline: "AI, as an\nOperating System.",
        subtext: `${BRAND_NAME} — enterprise AI OS for banking teams`,
        style: "dark-hook",
      }}
    />

    {/* Scene 02: Two kinds of work — 6s */}
    <Composition
      id="wb3-problem-02"
      component={() => (
        <FloatingCard
          bg={LINEN}
          cardBg={CARD_DARK}
          headline={"Two kinds of work\neat the day."}
          subheadline="Complex multi-step work + high-frequency trivial work — both uncaptured"
          enterAt={0}
        >
          <ClaudeCliContent
            phase="OBSERVE"
            startFrame={12}
            userTypingSpeed={1.8}
            assistantLineDelay={14}
            toolCallDelay={10}
            turnGap={18}
            turns={TWO_KINDS_TURNS}
          />
        </FloatingCard>
      )}
      durationInFrames={6 * FPS}
      fps={FPS}
      width={WIDTH}
      height={HEIGHT}
      defaultProps={{}}
    />

    {/* Scene 03: /extract-harness invocation — 5s */}
    <Composition
      id="wb3-invoke-03"
      component={() => (
        <FloatingCard
          bg={LINEN}
          cardBg={CARD_DARK}
          headline={"One command.\nOne OS."}
          subheadline="/extract-harness --enterprise — regulated-env distribution"
          enterAt={0}
        >
          <TerminalContent
            prompt={BRAND_PROMPT}
            command="/extract-harness --enterprise --target claude-workbench"
            startFrame={14}
            typingSpeed={1.6}
            lineDelay={8}
            outputLines={[
              { text: "Auditing 60 source skills...", color: "#9CA3AF" },
              { text: "  KEEP: 41  ·  ADAPT: 4  ·  STRIP: 15", color: "#A3E635" },
              { text: "Stripping personal-system references...", color: "#9CA3AF" },
              { text: "Writing templates/ knowledge/ security/ history/", color: "#9CA3AF" },
              { text: "Installing PII pre-commit hook...", color: "#9CA3AF" },
              { text: "✓ claude-workbench ready.  41 skills.  0 findings.", color: "#6EE7B7", bold: true },
            ]}
          />
        </FloatingCard>
      )}
      durationInFrames={5 * FPS}
      fps={FPS}
      width={WIDTH}
      height={HEIGHT}
      defaultProps={{}}
    />

    {/*
      Scene 04: The OS — skills, audit, guards. snapFromFull=true because the
      previous scene is a floating card and the transition into this three-panel
      uses zoomin xfade.
    */}
    <Composition
      id="wb3-os-04"
      component={() => (
        <ThreePanelScene
          phaseLabel="BUILD · /extract-harness --enterprise"
          headline={"Skills. Audit.\nGuards."}
          subheadline="41 skills · PII hook · constitutional rules · git-sourced audit"
          leftContent={
            <ClaudeCliContent
              phase="BUILD"
              startFrame={10}
              userTypingSpeed={1.8}
              assistantLineDelay={14}
              toolCallDelay={9}
              turnGap={14}
              turns={OS_BUILD_TURNS}
            />
          }
          bottomContent={<GuaranteesCard />}
          bottomCardBg={CARD_WHITE}
          bottomRevealFrame={200}
          leftWidthPct={52}
          leftDim={1.0}
          snapFromFull={true}
        />
      )}
      durationInFrames={9 * FPS}
      fps={FPS}
      width={WIDTH}
      height={HEIGHT}
      defaultProps={{}}
    />

    {/* Scene 05: Complex work captured once — 6s */}
    <Composition
      id="wb3-complex-05"
      component={() => (
        <FloatingCard
          bg={LINEN}
          cardBg="#0D1117"
          headline={"Complex work,\ncaptured once."}
          subheadline="/incident-postmortem · /architecture-review — ISC-gated, reusable forever"
          enterAt={0}
        >
          <MarkdownPRDContent
            startFrame={12}
            itemDelay={22}
            title="/incident-postmortem"
            phase="Blameless · 5-Whys · ALGORITHM loop"
            items={[
              { text: "Timeline: incident → detection → mitigation → resolution", tag: "OBSERVE" },
              { text: "5-Whys: root cause + contributing factors",                tag: "THINK" },
              { text: "Action items with owners, due dates, success criteria",    tag: "PLAN" },
              { text: "Regulatory impact (OSFI/PIPEDA flags auto-surfaced)",      tag: "VERIFY" },
              { text: "Lesson logged to history/lessons-learned/{project}/",      tag: "LEARN" },
            ]}
          />
        </FloatingCard>
      )}
      durationInFrames={6 * FPS}
      fps={FPS}
      width={WIDTH}
      height={HEIGHT}
      defaultProps={{}}
    />

    {/*
      Scene 06: Trivial work automated. snapFromFull=true — floating → three_panel
      uses zoomin xfade.
    */}
    <Composition
      id="wb3-trivial-06"
      component={() => (
        <ThreePanelScene
          phaseLabel="EXECUTE · daily rituals"
          headline={"Trivial work,\nautomated."}
          subheadline="10 daily skills: standup, AC, release notes, DoR, retro, meetings, more"
          leftContent={
            <ClaudeCliContent
              phase="EXECUTE"
              startFrame={10}
              userTypingSpeed={2.0}
              assistantLineDelay={14}
              toolCallDelay={8}
              turnGap={16}
              turns={TRIVIAL_AUTOMATION_TURNS}
            />
          }
          bottomContent={<RitualsCard />}
          bottomCardBg={CARD_WHITE}
          bottomRevealFrame={180}
          leftWidthPct={52}
          leftDim={1.0}
          snapFromFull={true}
        />
      )}
      durationInFrames={8 * FPS}
      fps={FPS}
      width={WIDTH}
      height={HEIGHT}
      defaultProps={{}}
    />

    {/* Scene 07: Actual /standup-brief output — 6s */}
    <Composition
      id="wb3-output-07"
      component={() => (
        <FloatingCard
          bg={LINEN}
          cardBg={CARD_WHITE}
          headline={"Actual output.\nIn seconds."}
          subheadline="/standup-brief · git log + Jira + yesterday's notes → shareable doc"
          enterAt={0}
        >
          <StandupDocContent />
        </FloatingCard>
      )}
      durationInFrames={6 * FPS}
      fps={FPS}
      width={WIDTH}
      height={HEIGHT}
      defaultProps={{}}
    />

    {/* Scene 08: Close TitleCard — 5s */}
    <Composition
      id="wb3-close-08"
      component={TitleCard as any}
      durationInFrames={5 * FPS}
      fps={FPS}
      width={WIDTH}
      height={HEIGHT}
      defaultProps={{
        headline: `${SKILL_AFTER} skills. Audit-ready.\nYour team's OS.`,
        subtext: `${BRAND_NAME} — TD Innovation Week 2026-04-20`,
        style: "dark-close",
      }}
    />
  </>
);
