/**
 * TerminalContent.tsx — Dark terminal card content for demo-skill video.
 *
 * Renders inside FloatingCard (cardBg = CARD_DARK).
 * Character-by-character command typing → sequential output line reveal.
 * All timing is frame-based; pass startFrame to stagger within a scene.
 */

import React from "react";
import { interpolate, useCurrentFrame, useVideoConfig } from "remotion";

interface OutputLine {
  text: string;
  /** Color override — default: #A3E635 (lime) */
  color?: string;
  /** Bold */
  bold?: boolean;
  /** Indent level (×16px) */
  indent?: number;
}

export interface TerminalContentProps {
  /** Prompt prefix */
  prompt?: string;
  /** Command text to type character-by-character */
  command: string;
  /** Output lines revealed after typing completes */
  outputLines?: OutputLine[];
  /** Frame at which typing begins (relative to scene start) */
  startFrame?: number;
  /** Chars per frame while typing (default 2) */
  typingSpeed?: number;
  /** Frames between each output line appearing (default 4) */
  lineDelay?: number;
}

const TERM_BG = "#18181B";
const PROMPT_COLOR = "#F59E0B";   // amber — matches Dracula-ish palette
const COMMAND_COLOR = "#FFFFFF";
const CURSOR_COLOR = "#F59E0B";
const DIM = "#6B7280";

export const TerminalContent: React.FC<TerminalContentProps> = ({
  prompt = "jarvis > ",
  command,
  outputLines = [],
  startFrame = 0,
  typingSpeed = 2,
  lineDelay = 5,
}) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  const elapsed = Math.max(0, frame - startFrame);

  // — Typing: reveal chars at typingSpeed chars/frame —
  const charsToShow = Math.min(
    command.length,
    Math.floor(elapsed * typingSpeed)
  );
  const typingDone = charsToShow >= command.length;
  const typingDoneFrame = Math.ceil(command.length / typingSpeed);

  // — Cursor blink: 0.5s cycle —
  const cursorVisible = Math.floor((frame / fps) * 2) % 2 === 0;

  // — Output lines: each appears lineDelay frames after previous —
  const outputElapsed = typingDone
    ? Math.max(0, elapsed - typingDoneFrame - 4) // 4 frame pause after enter
    : 0;

  return (
    <div
      style={{
        backgroundColor: TERM_BG,
        borderRadius: 10,
        padding: "28px 32px",
        fontFamily: "'Cascadia Code', 'Fira Code', 'Courier New', monospace",
        fontSize: 22,
        lineHeight: 1.6,
      }}
    >
      {/* Prompt + typing command */}
      <div style={{ display: "flex", alignItems: "center", gap: 0 }}>
        <span style={{ color: PROMPT_COLOR, fontWeight: 600 }}>{prompt}</span>
        <span style={{ color: COMMAND_COLOR }}>
          {command.slice(0, charsToShow)}
        </span>
        {/* Blinking cursor */}
        {!typingDone || cursorVisible ? (
          <span
            style={{
              display: "inline-block",
              width: 3,
              height: "1em",
              backgroundColor: CURSOR_COLOR,
              marginLeft: 2,
              verticalAlign: "middle",
              opacity: typingDone && !cursorVisible ? 0 : 1,
            }}
          />
        ) : null}
      </div>

      {/* Output lines — staggered reveal */}
      {outputLines.map((line, i) => {
        const lineStart = i * lineDelay;
        const lineAlpha = interpolate(
          outputElapsed,
          [lineStart, lineStart + 3],
          [0, 1],
          { extrapolateLeft: "clamp", extrapolateRight: "clamp" }
        );
        const lineY = interpolate(
          outputElapsed,
          [lineStart, lineStart + 3],
          [8, 0],
          { extrapolateLeft: "clamp", extrapolateRight: "clamp" }
        );

        return (
          <div
            key={i}
            style={{
              marginTop: i === 0 ? 6 : 0,
              opacity: lineAlpha,
              transform: `translateY(${lineY}px)`,
              paddingLeft: (line.indent ?? 0) * 16,
              color: line.color ?? "#A3E635",
              fontWeight: line.bold ? 700 : 400,
            }}
          >
            {line.text}
          </div>
        );
      })}
    </div>
  );
};
