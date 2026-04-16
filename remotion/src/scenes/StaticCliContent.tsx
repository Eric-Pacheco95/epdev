/**
 * StaticCliContent.tsx — Fully-revealed (no animation) version of ClaudeCliContent.
 *
 * Used in split-panel scenes where the left panel shows a "frozen" past conversation.
 * Same visual palette and font as ClaudeCliContent, but all turns are visible from frame 0.
 */

import React from "react";
import { ChatTurn } from "./ClaudeCliContent";

const USER_ARROW = "#F59E0B";
const USER_TEXT  = "#FFFFFF";
const ASST_TEXT  = "#D4D4D8";
const TOOL_NAME  = "#38BDF8";
const TOOL_TGT   = "#93C5FD";
const DIVIDER    = "#3F3F46";
const HEADER_DIM = "#71717A";
const PHASE_BG   = "#27272A";

export interface StaticCliContentProps {
  turns: ChatTurn[];
  phase?: string;
  /** Font size multiplier relative to default (19px), default 1.0 */
  scale?: number;
}

export const StaticCliContent: React.FC<StaticCliContentProps> = ({
  turns,
  phase,
  scale = 1.0,
}) => {
  const base = 19 * scale;
  const sm   = 15 * scale;
  const xs   = 13 * scale;

  return (
    <div style={{
      fontFamily: "'Cascadia Code', 'Fira Code', 'Courier New', monospace",
      fontSize: base,
      lineHeight: 1.65,
    }}>
      {/* Header bar */}
      <div style={{
        display: "flex",
        alignItems: "center",
        gap: 8,
        marginBottom: 18,
        paddingBottom: 12,
        borderBottom: `1px solid ${DIVIDER}`,
      }}>
        <div style={{
          width: 9 * scale,
          height: 9 * scale,
          borderRadius: "50%",
          backgroundColor: "#22C55E",
          flexShrink: 0,
        }} />
        <span style={{
          color: HEADER_DIM,
          fontSize: sm,
          fontFamily: "system-ui, -apple-system, sans-serif",
          letterSpacing: "0.05em",
        }}>
          Claude Code
        </span>
        {phase && (
          <span style={{
            marginLeft: "auto",
            backgroundColor: PHASE_BG,
            color: "#A1A1AA",
            fontSize: xs,
            fontFamily: "system-ui, -apple-system, sans-serif",
            letterSpacing: "0.08em",
            padding: `3px ${10 * scale}px`,
            borderRadius: 4,
            fontWeight: 600,
            textTransform: "uppercase" as const,
          }}>
            {phase}
          </span>
        )}
      </div>

      {/* All turns fully visible */}
      {turns.map((turn, i) => (
        <div key={i}>
          {i > 0 && (
            <div style={{
              height: 1,
              backgroundColor: DIVIDER,
              margin: `${6 * scale}px 0 ${14 * scale}px`,
              opacity: 0.35,
            }} />
          )}

          {turn.role === "user" ? (
            <div style={{ display: "flex", gap: 10 * scale, marginBottom: 18 * scale }}>
              <span style={{ color: USER_ARROW, fontWeight: 700, flexShrink: 0, fontSize: base * 1.05 }}>›</span>
              <span style={{ color: USER_TEXT }}>{turn.text}</span>
            </div>
          ) : (
            <div style={{ paddingLeft: 22 * scale, marginBottom: 18 * scale }}>
              {(turn.lines ?? []).map((line, li) => (
                <div key={li} style={{ color: ASST_TEXT, marginBottom: 3 }}>{line}</div>
              ))}
              {(turn.toolCalls ?? []).map((tc, ti) => (
                <div key={`tc${ti}`} style={{ display: "flex", gap: 8 * scale, marginBottom: 4 }}>
                  <span style={{ color: TOOL_NAME }}>&#8627;</span>
                  <span style={{ color: TOOL_NAME, fontWeight: 600 }}>{tc.tool}</span>
                  <span style={{ color: TOOL_TGT }}>{tc.target}</span>
                </div>
              ))}
            </div>
          )}
        </div>
      ))}
    </div>
  );
};
