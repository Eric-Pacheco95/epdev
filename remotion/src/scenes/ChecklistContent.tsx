/**
 * ChecklistContent.tsx — Animated ISC-style checklist for demo-skill video.
 *
 * Items reveal sequentially, then each checkbox fills in with a spring.
 * Designed as FloatingCard children (white card bg).
 */

import React from "react";
import { interpolate, spring, useCurrentFrame, useVideoConfig } from "remotion";

export interface ChecklistItem {
  text: string;
  /** Secondary label shown dimmer after text */
  tag?: string;
}

export interface ChecklistContentProps {
  items: ChecklistItem[];
  /** Frame at which first item starts appearing */
  startFrame?: number;
  /** Frames between each item reveal */
  itemDelay?: number;
  /** Frames after item appears before checkbox fills */
  checkDelay?: number;
}

const GREEN = "#16A34A";
const BOX_EMPTY = "#D1D5DB";
const TEXT_COLOR = "#1A1917";
const TAG_COLOR = "#9CA3AF";

const CheckItem: React.FC<{
  item: ChecklistItem;
  revealFrame: number;
  checkFrame: number;
  frame: number;
  fps: number;
}> = ({ item, revealFrame, checkFrame, frame, fps }) => {
  // Item slides in
  const revealElapsed = Math.max(0, frame - revealFrame);
  const revealSpr = spring({
    fps,
    frame: revealElapsed,
    config: { damping: 22, stiffness: 140 },
    durationInFrames: 18,
  });
  const itemOpacity = interpolate(revealSpr, [0, 1], [0, 1]);
  const itemX = interpolate(revealSpr, [0, 1], [-20, 0]);

  // Checkbox fill (after checkDelay)
  const checkElapsed = Math.max(0, frame - checkFrame);
  const checkSpr = spring({
    fps,
    frame: checkElapsed,
    config: { damping: 18, stiffness: 200 },
    durationInFrames: 12,
  });
  const checkScale = interpolate(checkSpr, [0, 1], [0, 1]);
  const checkOpacity = interpolate(checkSpr, [0, 1], [0, 1]);
  const isChecked = frame >= checkFrame;

  return (
    <div
      style={{
        display: "flex",
        alignItems: "center",
        gap: 20,
        opacity: itemOpacity,
        transform: `translateX(${itemX}px)`,
        marginBottom: 22,
      }}
    >
      {/* Checkbox */}
      <div
        style={{
          width: 28,
          height: 28,
          borderRadius: 6,
          border: `2.5px solid ${isChecked ? GREEN : BOX_EMPTY}`,
          backgroundColor: isChecked ? GREEN : "transparent",
          flexShrink: 0,
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          transition: "border-color 0.1s",
          transform: `scale(${isChecked ? 1 : 1})`,
        }}
      >
        {/* Checkmark */}
        <svg
          width="16"
          height="16"
          viewBox="0 0 16 16"
          fill="none"
          style={{ opacity: checkOpacity, transform: `scale(${checkScale})` }}
        >
          <path
            d="M3 8l3.5 3.5L13 4"
            stroke="white"
            strokeWidth="2.2"
            strokeLinecap="round"
            strokeLinejoin="round"
          />
        </svg>
      </div>

      {/* Text */}
      <div>
        <span
          style={{
            fontFamily: "system-ui, -apple-system, sans-serif",
            fontSize: 24,
            fontWeight: isChecked ? 500 : 400,
            color: isChecked ? TEXT_COLOR : "#6B7280",
            letterSpacing: "-0.2px",
          }}
        >
          {item.text}
        </span>
        {item.tag && (
          <span
            style={{
              marginLeft: 12,
              fontFamily: "'Cascadia Code', monospace",
              fontSize: 16,
              color: TAG_COLOR,
              backgroundColor: "#F3F4F6",
              padding: "2px 8px",
              borderRadius: 4,
            }}
          >
            {item.tag}
          </span>
        )}
      </div>
    </div>
  );
};

export const ChecklistContent: React.FC<ChecklistContentProps> = ({
  items,
  startFrame = 0,
  itemDelay = 20,
  checkDelay = 16,
}) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  return (
    <div style={{ padding: "8px 0" }}>
      {items.map((item, i) => {
        const revealFrame = startFrame + i * itemDelay;
        const checkFrame = revealFrame + checkDelay;
        return (
          <CheckItem
            key={i}
            item={item}
            revealFrame={revealFrame}
            checkFrame={checkFrame}
            frame={frame}
            fps={fps}
          />
        );
      })}
    </div>
  );
};
