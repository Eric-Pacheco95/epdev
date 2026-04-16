/**
 * ThreePanelScene.tsx — Full-frame three-area split layout.
 *
 * Inspired by Windows window snapping (Win+Left, Win+Right+Arrow):
 *   Left half:        Terminal — active or past conversation context
 *   Top-right:        Scene headline + subheadline (context label)
 *   Bottom-right:     Optional content card (e.g., verdict table, checklist)
 *
 * Used in scenes where the CLI conversation "expands" to the left side
 * while new structured output appears on the right.
 *
 * bottomContent is optional — pass null to show an empty placeholder.
 * bottomRevealFrame controls when the bottom-right card springs in.
 */

import React from "react";
import { interpolate, spring, useCurrentFrame, useVideoConfig } from "remotion";

const LINEN     = "#EBE7DB";
const CARD_DARK = "#18181B";
const CARD_WHITE = "#FFFFFF";

export interface ThreePanelSceneProps {
  /** Left panel: terminal conversation (animated ClaudeCliContent) */
  leftContent: React.ReactNode;
  /** Top-right: scene phase label (e.g. "PLAN · Architecture Review") */
  phaseLabel?: string;
  /** Top-right: main headline, Georgia serif */
  headline: string;
  /** Top-right: sub-headline, system-ui */
  subheadline?: string;
  /** Bottom-right: content card (verdict table, checklist, etc.) — optional */
  bottomContent?: React.ReactNode;
  /** Background color of the bottom-right card */
  bottomCardBg?: string;
  /**
   * Frame at which the bottom-right card springs in.
   * Set to 0 to show immediately, omit to hide until explicitly triggered.
   * Default: 0 (visible from start).
   */
  bottomRevealFrame?: number;
  /** Left panel width as percent of total frame width (default 52) */
  leftWidthPct?: number;
  /** Left panel card background (default CARD_DARK) */
  leftBg?: string;
  /** Top-right height as percent of right column height (default 44) */
  topRightHeightPct?: number;
  /** Left panel opacity — 1.0 for active context, 0.7 for dimmed past context */
  leftDim?: number;
  /**
   * When true, the left panel starts at full width (100%) and compresses to
   * leftWidthPct% in sync with the right column snap-in. Combined with a
   * zoomin xfade from the previous scene, this creates the Win+Left arrow
   * snap effect: the previous scene's full-screen terminal visually zooms
   * in, then the new scene's terminal compresses to the left as the right
   * panel slides in from off-screen right.
   * Default: false.
   */
  snapFromFull?: boolean;
}

export const ThreePanelScene: React.FC<ThreePanelSceneProps> = ({
  leftContent,
  phaseLabel,
  headline,
  subheadline,
  bottomContent,
  bottomCardBg = CARD_WHITE,
  bottomRevealFrame = 0,
  leftWidthPct = 52,
  leftBg = CARD_DARK,
  topRightHeightPct = 44,
  leftDim = 1.0,
  snapFromFull = false,
}) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  // Top-right headline: fade + slide down (frames 8→30)
  const headlineOp = interpolate(frame, [8, 30], [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });
  const headlineTy = interpolate(frame, [8, 30], [-16, 0], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });

  // Bottom-right card: spring in after bottomRevealFrame
  const bottomElapsed = Math.max(0, frame - bottomRevealFrame);
  const bottomSpr = spring({
    fps,
    frame: bottomElapsed,
    config: { damping: 22, stiffness: 150 },
    durationInFrames: 24,
  });
  const bottomOp  = interpolate(bottomSpr, [0, 1], [0, 1]);
  const bottomTy  = interpolate(bottomSpr, [0, 1], [20, 0]);

  const rightWidthPct = 100 - leftWidthPct;

  // ── Snap-to-left entrance animation ──────────────────────────────────────
  // Simulates the "Win+Left arrow" snap. Two variants:
  //
  // snapFromFull=true (recommended with zoomin xfade):
  //   1. Previous scene terminal zooms in via xfade
  //   2. New scene: left terminal STARTS at 100% width, compresses to leftWidthPct%
  //   3. Simultaneously: right column slides in from 520px off-screen right
  //   → Effect: terminal appears to snap to left half, right panel fills the gap
  //
  // snapFromFull=false (default):
  //   Left terminal is already settled at leftWidthPct%; right snaps in from right
  const snapSpr = spring({
    fps,
    frame: Math.min(frame, 50), // entrance phase only
    config: { damping: 24, stiffness: 210 },
    durationInFrames: 32,
  });

  // Left panel width: full (100%) → leftWidthPct when snapFromFull, else fixed
  const animatedLeftPct = snapFromFull
    ? interpolate(snapSpr, [0, 1], [100, leftWidthPct])
    : leftWidthPct;

  const rightTx = interpolate(snapSpr, [0, 1], [520, 0]);
  const rightOp = interpolate(snapSpr, [0.1, 0.8], [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });

  return (
    <div
      style={{
        width: 1920,
        height: 1080,
        backgroundColor: LINEN,
        display: "flex",
        padding: 36,
        gap: 24,
        boxSizing: "border-box" as const,
      }}
    >
      {/* ── Left panel: terminal (full height) — compresses from 100% when snapFromFull ── */}
      <div
        style={{
          width: `${animatedLeftPct}%`,
          flexShrink: 0,
          backgroundColor: leftBg,
          borderRadius: 18,
          padding: 40,
          opacity: leftDim,
          overflow: "hidden",
          display: "flex",
          flexDirection: "column" as const,
        }}
      >
        {leftContent}
      </div>

      {/* ── Right column: snaps in from the right (Win+Left snap effect) ── */}
      <div
        style={{
          flex: 1,
          display: "flex",
          flexDirection: "column" as const,
          gap: 20,
          minWidth: 0,
          opacity: rightOp,
          transform: `translateX(${rightTx}px)`,
        }}
      >
        {/* Top-right: scene context text */}
        <div
          style={{
            height: `${topRightHeightPct}%`,
            opacity: headlineOp,
            transform: `translateY(${headlineTy}px)`,
            display: "flex",
            flexDirection: "column" as const,
            justifyContent: "center",
            padding: "20px 8px",
          }}
        >
          {phaseLabel && (
            <div
              style={{
                fontFamily: "system-ui, -apple-system, sans-serif",
                fontSize: 13,
                fontWeight: 700,
                letterSpacing: "0.12em",
                textTransform: "uppercase" as const,
                color: "#9CA3AF",
                marginBottom: 14,
              }}
            >
              {phaseLabel}
            </div>
          )}
          <div
            style={{
              fontFamily: "Georgia, 'Times New Roman', serif",
              fontSize: 38,
              fontWeight: 700,
              color: "#1A1917",
              lineHeight: 1.18,
              letterSpacing: "-0.5px",
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
                marginTop: 12,
                lineHeight: 1.5,
                letterSpacing: "-0.1px",
              }}
            >
              {subheadline}
            </div>
          )}
        </div>

        {/* Bottom-right: optional content card */}
        <div
          style={{
            flex: 1,
            opacity: bottomContent ? bottomOp : 0,
            transform: `translateY(${bottomContent ? bottomTy : 0}px)`,
            backgroundColor: bottomCardBg,
            borderRadius: 18,
            padding: 32,
            overflow: "hidden",
          }}
        >
          {bottomContent}
        </div>
      </div>
    </div>
  );
};
