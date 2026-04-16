/**
 * FolderViewContent.tsx — Animated file-browser card.
 *
 * Simulates Eric clicking into the output folder and finding the rendered MP4.
 * Files list one by one (spring entrance), MP4 row highlights, play button appears.
 * Designed for FloatingCard with cardBg={CARD_WHITE}.
 */

import React from "react";
import { interpolate, spring, useCurrentFrame, useVideoConfig } from "remotion";

const FOLDER_COLOR = "#F59E0B";  // amber — folder icon
const MP4_COLOR    = "#16A34A";  // green — video file
const PY_COLOR     = "#3B82F6";  // blue — python file
const MD_COLOR     = "#8B5CF6";  // purple — markdown file
const DIM          = "#9CA3AF";
const TEXT         = "#1A1917";
const HIGHLIGHT_BG = "#F0FDF4";  // green-50 for highlighted row
const PLAY_BG      = "#16A34A";

interface FileRow {
  name: string;
  type: "mp4" | "py" | "md" | "txt";
  size: string;
  duration?: string;
  highlight?: boolean;
}

const FILE_ICON: Record<string, string> = {
  mp4: "▶",
  py:  "🐍",
  md:  "📄",
  txt: "📝",
};

const FILE_COLOR: Record<string, string> = {
  mp4: MP4_COLOR,
  py:  PY_COLOR,
  md:  MD_COLOR,
  txt: DIM,
};

export interface FolderViewContentProps {
  folderPath?: string;
  files?: FileRow[];
  /** Frame at which first file appears */
  startFrame?: number;
  /** Frames between each file row appearing */
  fileDelay?: number;
  /** Frames after MP4 appears before it highlights */
  highlightDelay?: number;
}

export const FolderViewContent: React.FC<FolderViewContentProps> = ({
  folderPath = "memory/work/td-innovation-keynote/",
  files = [
    { name: "keynote_2026-04-15.md",              type: "md",  size: "28 KB" },
    { name: "scene_definitions.py",                type: "py",  size: "4.1 KB" },
    { name: "jarvis_skill_demo_2026-04-15.mp4",   type: "mp4", size: "21.6 MB", duration: "2:26", highlight: true },
  ],
  startFrame = 30,
  fileDelay = 22,
  highlightDelay = 16,
}) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  // Folder path reveal
  const pathSpr = spring({
    fps,
    frame: Math.max(0, frame - startFrame + 8),
    config: { damping: 20, stiffness: 140 },
    durationInFrames: 18,
  });
  const pathOp = interpolate(pathSpr, [0, 1], [0, 1]);

  // Find the MP4 (highlighted) file index
  const mpIdx = files.findIndex(f => f.highlight);

  return (
    <div style={{ fontFamily: "system-ui, -apple-system, sans-serif" }}>
      {/* Breadcrumb path */}
      <div
        style={{
          opacity: pathOp,
          display: "flex",
          alignItems: "center",
          gap: 6,
          marginBottom: 24,
          padding: "8px 12px",
          backgroundColor: "#F9FAFB",
          borderRadius: 6,
          border: "1px solid #E5E7EB",
        }}
      >
        <span style={{ fontSize: 18, color: FOLDER_COLOR }}>📁</span>
        <span
          style={{
            fontFamily: "'Cascadia Code', 'Fira Code', monospace",
            fontSize: 17,
            color: "#374151",
            letterSpacing: "-0.3px",
          }}
        >
          {folderPath}
        </span>
      </div>

      {/* Column header */}
      <div
        style={{
          opacity: pathOp,
          display: "grid",
          gridTemplateColumns: "1fr 80px 60px",
          padding: "0 12px 8px",
          borderBottom: "1px solid #E5E7EB",
          marginBottom: 4,
        }}
      >
        {["Name", "Size", ""].map((h, i) => (
          <span key={i} style={{ fontSize: 13, color: DIM, fontWeight: 600, textTransform: "uppercase", letterSpacing: "0.05em" }}>
            {h}
          </span>
        ))}
      </div>

      {/* File rows */}
      {files.map((file, fi) => {
        const revealAt = startFrame + fi * fileDelay;
        const elapsed = Math.max(0, frame - revealAt);
        const spr = spring({
          fps,
          frame: elapsed,
          config: { damping: 20, stiffness: 150 },
          durationInFrames: 16,
        });
        const rowOp = interpolate(spr, [0, 1], [0, 1]);
        const rowX = interpolate(spr, [0, 1], [-16, 0]);

        // Highlight animation for MP4 file
        const isHighlight = file.highlight;
        const hlStart = revealAt + highlightDelay;
        const hlElapsed = Math.max(0, frame - hlStart);
        const hlSpr = spring({
          fps,
          frame: hlElapsed,
          config: { damping: 18, stiffness: 120 },
          durationInFrames: 20,
        });
        const hlBg = isHighlight
          ? interpolate(hlSpr, [0, 1], [0, 1])
          : 0;

        // Play button — appears after highlight
        const playStart = hlStart + 20;
        const playElapsed = Math.max(0, frame - playStart);
        const playSpr = spring({
          fps,
          frame: playElapsed,
          config: { damping: 16, stiffness: 200 },
          durationInFrames: 14,
        });
        const playScale = interpolate(playSpr, [0, 1], [0, 1]);
        const playOp = interpolate(playSpr, [0, 1], [0, 1]);

        return (
          <div
            key={fi}
            style={{
              opacity: rowOp,
              transform: `translateX(${rowX}px)`,
              display: "grid",
              gridTemplateColumns: "1fr 80px 60px",
              alignItems: "center",
              padding: "10px 12px",
              borderRadius: 6,
              backgroundColor: isHighlight ? `rgba(240, 253, 244, ${hlBg})` : "transparent",
              border: isHighlight ? `1px solid rgba(22, 163, 74, ${hlBg * 0.3})` : "1px solid transparent",
              marginBottom: 4,
            }}
          >
            {/* Name + icon */}
            <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
              <span style={{ fontSize: 18, color: FILE_COLOR[file.type], flexShrink: 0 }}>
                {FILE_ICON[file.type]}
              </span>
              <span
                style={{
                  fontFamily: "'Cascadia Code', 'Fira Code', monospace",
                  fontSize: 17,
                  color: isHighlight ? MP4_COLOR : TEXT,
                  fontWeight: isHighlight ? 600 : 400,
                  letterSpacing: "-0.2px",
                }}
              >
                {file.name}
              </span>
              {file.duration && (
                <span
                  style={{
                    marginLeft: 8,
                    fontSize: 13,
                    color: DIM,
                    backgroundColor: "#F3F4F6",
                    padding: "2px 6px",
                    borderRadius: 4,
                  }}
                >
                  {file.duration}
                </span>
              )}
            </div>

            {/* Size */}
            <span style={{ fontSize: 15, color: DIM, textAlign: "right" }}>{file.size}</span>

            {/* Play button (MP4 only) */}
            <div style={{ display: "flex", justifyContent: "center" }}>
              {isHighlight && (
                <div
                  style={{
                    opacity: playOp,
                    transform: `scale(${playScale})`,
                    width: 32,
                    height: 32,
                    borderRadius: "50%",
                    backgroundColor: PLAY_BG,
                    display: "flex",
                    alignItems: "center",
                    justifyContent: "center",
                    boxShadow: "0 2px 8px rgba(22, 163, 74, 0.35)",
                  }}
                >
                  <span style={{ color: "#FFFFFF", fontSize: 12, marginLeft: 2 }}>▶</span>
                </div>
              )}
            </div>
          </div>
        );
      })}

      {/* Footer note */}
      {(() => {
        const noteAt = startFrame + files.length * fileDelay + highlightDelay + 28;
        const noteOp = interpolate(
          frame,
          [noteAt, noteAt + 8],
          [0, 1],
          { extrapolateLeft: "clamp", extrapolateRight: "clamp" }
        );
        return (
          <div
            style={{
              opacity: noteOp,
              marginTop: 20,
              padding: "12px 16px",
              backgroundColor: "#F0FDF4",
              borderRadius: 8,
              borderLeft: "3px solid #16A34A",
              fontFamily: "'Cascadia Code', monospace",
              fontSize: 15,
              color: "#14532D",
            }}
          >
            P1-5 ✓ — full demo video under 3 minutes &nbsp;|&nbsp; P1-6 ✓ — no personal data in output
          </div>
        );
      })()}
    </div>
  );
};
