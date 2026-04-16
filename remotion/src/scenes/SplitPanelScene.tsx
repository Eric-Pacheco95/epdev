/**
 * SplitPanelScene.tsx — Full-frame two-panel layout for split-screen scenes.
 *
 * Left panel: dimmed dark card — shows "past" conversation context (static)
 * Right panel: headline + animated content card — shows new content
 *
 * Used in scenes 3, 4, and 8 to create the "camera zooms into CLI, new content
 * appears alongside" visual narrative. Pairs with StaticCliContent for the left.
 */

import React from "react";
import { interpolate, spring, useCurrentFrame, useVideoConfig } from "remotion";

const LINEN     = "#EBE7DB";
const CARD_DARK = "#18181B";

export interface SplitPanelSceneProps {
  /** Left panel content — typically <StaticCliContent /> */
  leftContent: React.ReactNode;
  /** Right panel headline (Georgia serif) */
  headline: string;
  /** Right panel sub-headline (system-ui) */
  subheadline?: string;
  /** Right panel main content — placed inside a card */
  children: React.ReactNode;
  /** Left panel width as percent of total frame (default 52) */
  leftWidthPct?: number;
  /** Left panel opacity — lower = more dimmed (default 0.78) */
  leftDim?: number;
  /** Right content card background color (default CARD_DARK) */
  rightCardBg?: string;
}

export const SplitPanelScene: React.FC<SplitPanelSceneProps> = ({
  leftContent,
  headline,
  subheadline,
  children,
  leftWidthPct = 52,
  leftDim = 0.78,
  rightCardBg = CARD_DARK,
}) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  // Right headline: fade + slide down (frames 5→28)
  const headlineOp = interpolate(frame, [5, 28], [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });
  const headlineTy = interpolate(frame, [5, 28], [-14, 0], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });

  // Right content card: spring entrance (starts frame 20)
  const contentSpr = spring({
    fps,
    frame: Math.max(0, frame - 20),
    config: { damping: 22, stiffness: 155 },
    durationInFrames: 22,
  });
  const contentOp = interpolate(contentSpr, [0, 1], [0, 1]);
  const contentTx = interpolate(contentSpr, [0, 1], [28, 0]);

  return (
    <div
      style={{
        width: 1920,
        height: 1080,
        backgroundColor: LINEN,
        display: "flex",
        padding: 40,
        gap: 28,
        boxSizing: "border-box" as const,
      }}
    >
      {/* ── Left panel: dimmed past context ── */}
      <div
        style={{
          width: `${leftWidthPct}%`,
          flexShrink: 0,
          backgroundColor: CARD_DARK,
          borderRadius: 20,
          padding: 44,
          opacity: leftDim,
          overflow: "hidden",
        }}
      >
        {leftContent}
      </div>

      {/* ── Right panel: headline + animated card ── */}
      <div
        style={{
          flex: 1,
          display: "flex",
          flexDirection: "column" as const,
          gap: 20,
          minWidth: 0,
        }}
      >
        {/* Headline block */}
        <div
          style={{
            opacity: headlineOp,
            transform: `translateY(${headlineTy}px)`,
            flexShrink: 0,
          }}
        >
          <div
            style={{
              fontFamily: "Georgia, 'Times New Roman', serif",
              fontSize: 34,
              fontWeight: 700,
              color: "#1A1917",
              lineHeight: 1.22,
              letterSpacing: "-0.4px",
              whiteSpace: "pre-line" as const,
            }}
          >
            {headline}
          </div>
          {subheadline && (
            <div
              style={{
                fontFamily: "system-ui, -apple-system, sans-serif",
                fontSize: 17,
                color: "#6B7280",
                marginTop: 8,
                letterSpacing: "-0.2px",
              }}
            >
              {subheadline}
            </div>
          )}
        </div>

        {/* Content card */}
        <div
          style={{
            flex: 1,
            backgroundColor: rightCardBg,
            borderRadius: 20,
            padding: 38,
            opacity: contentOp,
            transform: `translateX(${contentTx}px)`,
            overflow: "hidden",
          }}
        >
          {children}
        </div>
      </div>
    </div>
  );
};
