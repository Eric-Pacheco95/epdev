/**
 * FloatingCard.tsx — Core visual pattern matching Claude's demo video aesthetic.
 *
 * Linen background + white (or dark) rounded card, spring entrance,
 * optional headline above, optional hold-phase zoom.
 * Every demo-skill scene is a FloatingCard with different children.
 */

import React from "react";
import {
  AbsoluteFill,
  interpolate,
  spring,
  useCurrentFrame,
  useVideoConfig,
} from "remotion";

export const LINEN = "#EBE7DB";   // warm off-white matching Claude reference
export const CARD_WHITE = "#FFFFFF";
export const CARD_DARK = "#18181B";
export const INK = "#1A1917";      // near-black for headlines

export interface FloatingCardProps {
  /** Linen (default) or custom background */
  bg?: string;
  /** Card background color */
  cardBg?: string;
  /** Headline text displayed above the card (serif) */
  headline?: string;
  /** Sub-headline below the main headline */
  subheadline?: string;
  /** Frame at which the card starts entering */
  enterAt?: number;
  /** Target hold-phase scale — set >1 for slow zoom-in effect */
  holdZoom?: number;
  /** Horizontal pan in px during hold phase (positive = pan left) */
  holdPanX?: number;
  /** Card padding */
  padding?: number | string;
  /** Max card width in px */
  maxWidth?: number;
  /** Extra styles applied to the card wrapper */
  cardStyle?: React.CSSProperties;
  children?: React.ReactNode;
}

export const FloatingCard: React.FC<FloatingCardProps> = ({
  bg = LINEN,
  cardBg = CARD_WHITE,
  headline,
  subheadline,
  enterAt = 0,
  holdZoom = 1.0,
  holdPanX = 0,
  padding = "40px 48px",
  maxWidth = 1280,
  cardStyle = {},
  children,
}) => {
  const frame = useCurrentFrame();
  const { fps, durationInFrames } = useVideoConfig();

  // — Card spring entrance (scale + translateY) —
  const entranceFrames = Math.max(0, frame - enterAt);
  const spr = spring({
    fps,
    frame: entranceFrames,
    config: { damping: 18, stiffness: 110, mass: 0.9 },
    durationInFrames: 28,
  });

  const cardScale = interpolate(spr, [0, 1], [0.91, 1.0]);
  const cardY = interpolate(spr, [0, 1], [28, 0]);

  // — Slow hold-phase zoom (after entrance settles) —
  const holdFrames = Math.max(0, entranceFrames - 28);
  const holdDuration = durationInFrames - enterAt - 28;
  const zoomProgress = interpolate(holdFrames, [0, Math.max(holdDuration, 1)], [1, holdZoom], {
    extrapolateRight: "clamp",
  });
  const panX = interpolate(holdFrames, [0, Math.max(holdDuration, 1)], [0, holdPanX], {
    extrapolateRight: "clamp",
  });

  // — Headline stagger: appears 6 frames after card —
  const headlineFrame = Math.max(0, frame - enterAt - 4);
  const headlineSpr = spring({
    fps,
    frame: headlineFrame,
    config: { damping: 20, stiffness: 130 },
    durationInFrames: 22,
  });
  const headlineOpacity = interpolate(headlineSpr, [0, 1], [0, 1]);
  const headlineY = interpolate(headlineSpr, [0, 1], [16, 0]);

  // — Subheadline staggered further (12 frames after card) —
  const subFrame = Math.max(0, frame - enterAt - 10);
  const subSpr = spring({
    fps,
    frame: subFrame,
    config: { damping: 20, stiffness: 130 },
    durationInFrames: 22,
  });
  const subOpacity = interpolate(subSpr, [0, 1], [0, 1]);

  // — Scene fade-out —
  const fadeOutStart = durationInFrames - Math.floor(fps * 0.8);
  const fadeOut = interpolate(frame, [fadeOutStart, durationInFrames], [1, 0], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });

  // — Entry fade (first 8 frames from enterAt) —
  const entryFade = interpolate(frame, [enterAt, enterAt + 8], [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });

  const sceneOpacity = Math.min(entryFade, fadeOut);

  return (
    <AbsoluteFill style={{ backgroundColor: bg, overflow: "hidden" }}>
      <div
        style={{
          position: "absolute",
          inset: 0,
          display: "flex",
          flexDirection: "column",
          alignItems: "center",
          justifyContent: "center",
          padding: "80px 120px",
          opacity: sceneOpacity,
        }}
      >
        {/* Headline above the card */}
        {headline && (
          <div
            style={{
              opacity: headlineOpacity,
              transform: `translateY(${headlineY}px)`,
              marginBottom: 40,
              textAlign: "center",
              maxWidth: maxWidth,
            }}
          >
            <div
              style={{
                fontFamily: "Georgia, 'Times New Roman', serif",
                fontSize: 64,
                fontWeight: 700,
                color: INK,
                letterSpacing: "-1.5px",
                lineHeight: 1.2,
                whiteSpace: "pre-line",
              }}
            >
              {headline}
            </div>
            {subheadline && (
              <div
                style={{
                  opacity: subOpacity,
                  fontFamily: "system-ui, -apple-system, sans-serif",
                  fontSize: 26,
                  color: "#6B6860",
                  marginTop: 18,
                  fontWeight: 400,
                  letterSpacing: "-0.2px",
                }}
              >
                {subheadline}
              </div>
            )}
          </div>
        )}

        {/* The floating card */}
        {children && (
          <div
            style={{
              width: "100%",
              maxWidth,
              transform: `scale(${cardScale * zoomProgress}) translateY(${cardY}px) translateX(${-panX}px)`,
              transformOrigin: "center center",
              backgroundColor: cardBg,
              borderRadius: 16,
              boxShadow: "0 4px 32px rgba(0,0,0,0.10), 0 1px 4px rgba(0,0,0,0.06)",
              padding,
              ...cardStyle,
            }}
          >
            {children}
          </div>
        )}
      </div>
    </AbsoluteFill>
  );
};
