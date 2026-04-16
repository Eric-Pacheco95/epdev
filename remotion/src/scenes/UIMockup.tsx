import React from "react";
import {
  AbsoluteFill,
  interpolate,
  useCurrentFrame,
  useVideoConfig,
} from "remotion";

export interface ConversationTurn {
  role: "user" | "assistant";
  text?: string;
  streaming?: boolean;
  text_blocks?: string[];
  highlight_text?: string;
}

export interface UIMockupProps {
  interface: "claude-ai-browser";
  conversation: ConversationTurn[];
}

// How many frames to reveal per character (streaming effect)
const CHARS_PER_FRAME = 3;
// Frame at which assistant response starts streaming
const STREAM_START_FRAME_OFFSET = 90; // ~1.5s after scene start

function HighlightedText({
  text,
  highlight,
}: {
  text: string;
  highlight?: string;
}) {
  if (!highlight || !text.includes(highlight)) {
    return <span>{text}</span>;
  }
  const parts = text.split(highlight);
  return (
    <>
      {parts.map((part, i) => (
        <React.Fragment key={i}>
          {part}
          {i < parts.length - 1 && (
            <span
              style={{
                backgroundColor: "#ff4d4d22",
                color: "#ff6b6b",
                fontWeight: 700,
                padding: "1px 4px",
                borderRadius: 3,
                border: "1px solid #ff4d4d44",
              }}
            >
              {highlight}
            </span>
          )}
        </React.Fragment>
      ))}
    </>
  );
}

function AssistantMessage({
  turn,
  frame,
  streamStartFrame,
  highlightText,
}: {
  turn: ConversationTurn;
  frame: number;
  streamStartFrame: number;
  highlightText?: string;
}) {
  const fullText = turn.text_blocks ? turn.text_blocks.join("") : turn.text ?? "";
  const elapsed = Math.max(0, frame - streamStartFrame);
  const charsToShow = elapsed * CHARS_PER_FRAME;
  const visibleText = fullText.slice(0, charsToShow);

  // Parse visible text into markdown-like lines for display
  const lines = visibleText.split("\n");

  return (
    <div
      style={{
        marginBottom: 20,
        padding: "16px 20px",
        background: "#1a1a2e",
        borderRadius: 12,
        border: "1px solid #2a2a4a",
        fontFamily: "'Cascadia Code', 'Courier New', monospace",
        fontSize: 15,
        lineHeight: 1.6,
        color: "#d0d0e8",
        whiteSpace: "pre-wrap",
        wordBreak: "break-word",
      }}
    >
      {lines.map((line, i) => {
        // Bold: **text**
        const boldProcessed = line.replace(/\*\*(.*?)\*\*/g, (_, m) => `__BOLD__${m}__ENDBOLD__`);
        const parts = boldProcessed.split(/(__BOLD__|__ENDBOLD__)/);
        let isBold = false;

        return (
          <div key={i}>
            {parts.map((part, j) => {
              if (part === "__BOLD__") { isBold = true; return null; }
              if (part === "__ENDBOLD__") { isBold = false; return null; }
              return (
                <span key={j} style={{ fontWeight: isBold ? 700 : 400 }}>
                  <HighlightedText text={part} highlight={highlightText} />
                </span>
              );
            })}
          </div>
        );
      })}
      {/* Streaming cursor */}
      {charsToShow < fullText.length && (
        <span style={{ opacity: Math.floor(frame / 15) % 2 === 0 ? 1 : 0, color: "#7c7ccc" }}>
          ▋
        </span>
      )}
    </div>
  );
}

export const UIMockup: React.FC<UIMockupProps> = ({ conversation }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  const fadeIn = interpolate(frame, [0, Math.floor(fps * 0.4)], [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });

  const streamStartFrame = STREAM_START_FRAME_OFFSET;

  return (
    <AbsoluteFill style={{ backgroundColor: "#0d0d1a", opacity: fadeIn }}>
      {/* Browser chrome */}
      <div
        style={{
          backgroundColor: "#1a1a2e",
          height: 44,
          display: "flex",
          alignItems: "center",
          padding: "0 20px",
          borderBottom: "1px solid #2a2a4a",
          gap: 8,
        }}
      >
        {/* Traffic lights */}
        {["#ff5f57", "#febc2e", "#28c840"].map((color, i) => (
          <div key={i} style={{ width: 12, height: 12, borderRadius: "50%", backgroundColor: color }} />
        ))}
        {/* URL bar */}
        <div
          style={{
            marginLeft: 20,
            flex: 1,
            maxWidth: 600,
            backgroundColor: "#0d0d1a",
            borderRadius: 6,
            padding: "4px 12px",
            fontSize: 13,
            color: "#6666aa",
            border: "1px solid #2a2a4a",
            fontFamily: "system-ui, sans-serif",
          }}
        >
          claude.ai/new
        </div>
      </div>

      {/* Main content area */}
      <div
        style={{
          display: "flex",
          height: "calc(100% - 44px)",
        }}
      >
        {/* Sidebar */}
        <div
          style={{
            width: 240,
            backgroundColor: "#12121f",
            borderRight: "1px solid #2a2a4a",
            padding: "20px 0",
          }}
        >
          <div style={{ padding: "0 16px", marginBottom: 20 }}>
            <div style={{ fontSize: 18, fontWeight: 700, color: "#f0f0f8", fontFamily: "system-ui" }}>
              Claude
            </div>
            <div style={{ fontSize: 11, color: "#4444aa", fontFamily: "system-ui", marginTop: 2 }}>
              Enterprise
            </div>
          </div>
          <div style={{ padding: "8px 16px", backgroundColor: "#1a1a2e", margin: "0 8px", borderRadius: 6 }}>
            <div style={{ fontSize: 13, color: "#8888cc", fontFamily: "system-ui" }}>
              TD Innovation Demo
            </div>
          </div>
        </div>

        {/* Chat area */}
        <div
          style={{
            flex: 1,
            padding: "32px 60px",
            overflowY: "hidden",
            maxWidth: 900,
            margin: "0 auto",
          }}
        >
          {conversation.map((turn, i) => {
            if (turn.role === "user") {
              return (
                <div
                  key={i}
                  style={{
                    marginBottom: 20,
                    padding: "14px 18px",
                    background: "#1e1e3a",
                    borderRadius: 12,
                    border: "1px solid #3a3a6a",
                    fontFamily: "'Cascadia Code', monospace",
                    fontSize: 13,
                    color: "#a0a0c8",
                    whiteSpace: "pre-wrap",
                    lineHeight: 1.5,
                  }}
                >
                  {turn.text}
                </div>
              );
            }
            return (
              <AssistantMessage
                key={i}
                turn={turn}
                frame={frame}
                streamStartFrame={streamStartFrame}
                highlightText={turn.highlight_text}
              />
            );
          })}
        </div>
      </div>
    </AbsoluteFill>
  );
};
