/**
 * ClaudeCliContent.tsx — Multi-turn Claude CLI dialog animation.
 *
 * Renders inside FloatingCard (cardBg = CARD_DARK).
 * User turns: character-by-character typing with blinking cursor.
 * Assistant turns: line-by-line reveal + tool-call badge rows.
 *
 * All timing is frame-based and computed automatically from content length.
 */

import React from "react";
import { interpolate, useCurrentFrame, useVideoConfig } from "remotion";

// ─── Palette ────────────────────────────────────────────────────────────────
const USER_ARROW = "#F59E0B";    // amber
const USER_TEXT  = "#FFFFFF";
const ASST_TEXT  = "#D4D4D8";   // light gray
const TOOL_NAME  = "#38BDF8";   // sky blue  ↳ ToolName
const TOOL_TGT   = "#93C5FD";   // lighter blue  → target
const DIVIDER    = "#3F3F46";   // zinc-700
const HEADER_DIM = "#71717A";   // zinc-500
const PHASE_BG   = "#27272A";   // zinc-800 for phase badge

// ─── Types ───────────────────────────────────────────────────────────────────
export interface ToolCall {
  tool: string;
  target: string;
}

export interface ChatTurn {
  role: "user" | "assistant";
  /** User: single string typed char-by-char */
  text?: string;
  /** Assistant: array of prose lines revealed sequentially */
  lines?: string[];
  /** Tool calls revealed after prose lines */
  toolCalls?: ToolCall[];
  /** Extra frames to pause after this turn completes before next turn starts */
  pauseAfter?: number;
  /**
   * If true, this turn appears fully revealed at frame 0 — no typing or fade animation.
   * Used for "past context" turns in split/three-panel scenes where earlier conversation
   * should be immediately visible so the viewer can focus on new animated turns.
   */
  instant?: boolean;
}

export interface ClaudeCliContentProps {
  turns: ChatTurn[];
  /** Algorithm phase label shown in header (e.g. "OBSERVE · THINK") */
  phase?: string;
  /** Frame at which first turn begins */
  startFrame?: number;
  /** Chars per frame for user typing (default 2.0) */
  userTypingSpeed?: number;
  /** Frames between each assistant prose line (default 18) */
  assistantLineDelay?: number;
  /** Frames between each tool-call badge (default 12) */
  toolCallDelay?: number;
  /** Frames of pause between turns (default 24) */
  turnGap?: number;
}

// ─── Timing helper ───────────────────────────────────────────────────────────
interface TurnTiming { start: number; end: number }

function buildTimings(
  turns: ChatTurn[],
  startFrame: number,
  userTypingSpeed: number,
  assistantLineDelay: number,
  toolCallDelay: number,
  turnGap: number,
): TurnTiming[] {
  const out: TurnTiming[] = [];
  let cursor = startFrame;

  for (const t of turns) {
    const s = cursor;
    let dur = 0;
    if (t.instant) {
      dur = 0; // instant turns consume no animation time
    } else if (t.role === "user") {
      dur = Math.ceil((t.text ?? "").length / userTypingSpeed);
    } else {
      dur =
        (t.lines ?? []).length * assistantLineDelay +
        (t.toolCalls ?? []).length * toolCallDelay;
    }
    out.push({ start: s, end: s + dur });
    cursor = s + dur + turnGap + (t.pauseAfter ?? 0);
  }
  return out;
}

// ─── Sub-components ──────────────────────────────────────────────────────────
const UserTurn: React.FC<{
  text: string;
  elapsed: number;
  frame: number;
  fps: number;
  typingSpeed: number;
}> = ({ text, elapsed, frame, fps, typingSpeed }) => {
  const chars = Math.min(text.length, Math.floor(elapsed * typingSpeed));
  const done = chars >= text.length;
  const cursorOn = Math.floor((frame / fps) * 2) % 2 === 0;

  return (
    <div style={{ display: "flex", gap: 10, marginBottom: 18 }}>
      <span style={{ color: USER_ARROW, fontWeight: 700, flexShrink: 0, fontSize: 20 }}>›</span>
      <span style={{ color: USER_TEXT }}>
        {text.slice(0, chars)}
        {(!done || cursorOn) && (
          <span
            style={{
              display: "inline-block",
              width: 2,
              height: "0.85em",
              backgroundColor: USER_ARROW,
              marginLeft: 2,
              verticalAlign: "middle",
              opacity: done && !cursorOn ? 0 : 1,
            }}
          />
        )}
      </span>
    </div>
  );
};

const AssistantTurn: React.FC<{
  lines: string[];
  toolCalls: ToolCall[];
  elapsed: number;
  lineDelay: number;
  toolDelay: number;
}> = ({ lines, toolCalls, elapsed, lineDelay, toolDelay }) => {
  return (
    <div style={{ paddingLeft: 22, marginBottom: 18 }}>
      {lines.map((line, li) => {
        const ls = li * lineDelay;
        const op = interpolate(elapsed, [ls, ls + 6], [0, 1], {
          extrapolateLeft: "clamp",
          extrapolateRight: "clamp",
        });
        const ty = interpolate(elapsed, [ls, ls + 6], [8, 0], {
          extrapolateLeft: "clamp",
          extrapolateRight: "clamp",
        });
        return (
          <div
            key={li}
            style={{
              opacity: op,
              transform: `translateY(${ty}px)`,
              color: ASST_TEXT,
              marginBottom: 3,
            }}
          >
            {line}
          </div>
        );
      })}

      {toolCalls.map((tc, ti) => {
        const ts = lines.length * lineDelay + ti * toolDelay;
        const op = interpolate(elapsed, [ts, ts + 5], [0, 1], {
          extrapolateLeft: "clamp",
          extrapolateRight: "clamp",
        });
        const ty = interpolate(elapsed, [ts, ts + 5], [6, 0], {
          extrapolateLeft: "clamp",
          extrapolateRight: "clamp",
        });
        return (
          <div
            key={`tc${ti}`}
            style={{
              opacity: op,
              transform: `translateY(${ty}px)`,
              display: "flex",
              gap: 8,
              marginBottom: 4,
            }}
          >
            <span style={{ color: TOOL_NAME }}>↳</span>
            <span style={{ color: TOOL_NAME, fontWeight: 600 }}>{tc.tool}</span>
            <span style={{ color: TOOL_TGT }}>{tc.target}</span>
          </div>
        );
      })}
    </div>
  );
};

// ─── Main component ──────────────────────────────────────────────────────────
export const ClaudeCliContent: React.FC<ClaudeCliContentProps> = ({
  turns,
  phase,
  startFrame = 35,
  userTypingSpeed = 2.0,
  assistantLineDelay = 18,
  toolCallDelay = 12,
  turnGap = 24,
}) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  const timings = buildTimings(
    turns,
    startFrame,
    userTypingSpeed,
    assistantLineDelay,
    toolCallDelay,
    turnGap,
  );

  return (
    <div
      style={{
        fontFamily: "'Cascadia Code', 'Fira Code', 'Courier New', monospace",
        fontSize: 19,
        lineHeight: 1.65,
      }}
    >
      {/* Header bar */}
      <div
        style={{
          display: "flex",
          alignItems: "center",
          gap: 8,
          marginBottom: 18,
          paddingBottom: 12,
          borderBottom: `1px solid ${DIVIDER}`,
        }}
      >
        <div
          style={{
            width: 9,
            height: 9,
            borderRadius: "50%",
            backgroundColor: "#22C55E",
            flexShrink: 0,
          }}
        />
        <span
          style={{
            color: HEADER_DIM,
            fontSize: 15,
            fontFamily: "system-ui, -apple-system, sans-serif",
            letterSpacing: "0.05em",
          }}
        >
          Claude Code
        </span>

        {phase && (
          <span
            style={{
              marginLeft: "auto",
              backgroundColor: PHASE_BG,
              color: "#A1A1AA",
              fontSize: 13,
              fontFamily: "system-ui, -apple-system, sans-serif",
              letterSpacing: "0.08em",
              padding: "3px 10px",
              borderRadius: 4,
              fontWeight: 600,
              textTransform: "uppercase",
            }}
          >
            {phase}
          </span>
        )}
      </div>

      {/* Turn rendering */}
      {turns.map((turn, i) => {
        const { start } = timings[i];
        // instant turns: treat elapsed as very large so all animations show fully-revealed
        const isInstant = turn.instant ?? false;
        const elapsed = isInstant ? 9999 : Math.max(0, frame - start);
        const fadeOp = isInstant ? 1 : interpolate(elapsed, [0, 5], [0, 1], {
          extrapolateLeft: "clamp",
          extrapolateRight: "clamp",
        });

        // Separator between turns — instant for instant turns, otherwise timed
        const sepOp = i > 0
          ? (isInstant ? 1 : interpolate(Math.max(0, frame - start + 2), [0, 5], [0, 1], {
              extrapolateLeft: "clamp",
              extrapolateRight: "clamp",
            }))
          : 0;

        return (
          <div key={i}>
            {i > 0 && (
              <div
                style={{
                  height: 1,
                  backgroundColor: DIVIDER,
                  margin: "6px 0 14px",
                  opacity: sepOp * 0.5,
                }}
              />
            )}
            <div style={{ opacity: fadeOp }}>
              {turn.role === "user" ? (
                <UserTurn
                  text={turn.text ?? ""}
                  elapsed={elapsed}
                  frame={frame}
                  fps={fps}
                  typingSpeed={userTypingSpeed}
                />
              ) : (
                <AssistantTurn
                  lines={turn.lines ?? []}
                  toolCalls={turn.toolCalls ?? []}
                  elapsed={elapsed}
                  lineDelay={assistantLineDelay}
                  toolDelay={toolCallDelay}
                />
              )}
            </div>
          </div>
        );
      })}
    </div>
  );
};
