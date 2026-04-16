import React from "react";
import {
  AbsoluteFill,
  interpolate,
  useCurrentFrame,
  useVideoConfig,
} from "remotion";

export interface TitleCardProps {
  headline: string;
  subtext?: string;
  style?: "dark-hook" | "dark-transition" | "dark-statement" | "dark-close";
}

const STYLES = {
  "dark-hook": {
    bg: "#0a0a0f",
    accentColor: "#4f8ef7",
    headlineSize: 72,
    subtextSize: 28,
  },
  "dark-transition": {
    bg: "#0f0f1a",
    accentColor: "#7c6af7",
    headlineSize: 60,
    subtextSize: 26,
  },
  "dark-statement": {
    bg: "#0a0a0f",
    accentColor: "#4fc4f7",
    headlineSize: 58,
    subtextSize: 24,
  },
  "dark-close": {
    bg: "#060609",
    accentColor: "#f7a84f",
    headlineSize: 80,
    subtextSize: 22,
  },
};

export const TitleCard: React.FC<TitleCardProps> = ({
  headline,
  subtext = "",
  style = "dark-hook",
}) => {
  const frame = useCurrentFrame();
  const { fps, durationInFrames } = useVideoConfig();

  const s = STYLES[style] ?? STYLES["dark-hook"];

  // Fade in over first 0.5s, fade out over last 0.4s
  const fadeInFrames = Math.floor(fps * 0.5);
  const fadeOutStart = durationInFrames - Math.floor(fps * 0.4);

  const opacity = interpolate(
    frame,
    [0, fadeInFrames, fadeOutStart, durationInFrames],
    [0, 1, 1, 0],
    { extrapolateLeft: "clamp", extrapolateRight: "clamp" }
  );

  // Subtle upward drift on entrance
  const translateY = interpolate(frame, [0, fadeInFrames], [18, 0], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });

  const lines = headline.split("\n");

  return (
    <AbsoluteFill
      style={{
        backgroundColor: s.bg,
        display: "flex",
        flexDirection: "column",
        alignItems: "center",
        justifyContent: "center",
        fontFamily: "'Cascadia Code', 'Fira Code', 'Consolas', monospace",
        padding: "80px 120px",
      }}
    >
      {/* Accent bar */}
      <div
        style={{
          width: 60,
          height: 4,
          backgroundColor: s.accentColor,
          borderRadius: 2,
          marginBottom: 40,
          opacity,
        }}
      />

      {/* Headline lines */}
      <div
        style={{
          opacity,
          transform: `translateY(${translateY}px)`,
          textAlign: "center",
        }}
      >
        {lines.map((line, i) => (
          <div
            key={i}
            style={{
              fontSize: s.headlineSize,
              fontWeight: 700,
              color: "#f0f0f8",
              lineHeight: 1.15,
              letterSpacing: "-0.5px",
              marginBottom: i < lines.length - 1 ? 8 : 0,
            }}
          >
            {line}
          </div>
        ))}
      </div>

      {/* Subtext */}
      {subtext && (
        <div
          style={{
            opacity: interpolate(
              frame,
              [fadeInFrames, fadeInFrames + Math.floor(fps * 0.3)],
              [0, opacity],
              { extrapolateLeft: "clamp", extrapolateRight: "clamp" }
            ),
            fontSize: s.subtextSize,
            color: "#8888aa",
            marginTop: 32,
            textAlign: "center",
            fontWeight: 400,
            letterSpacing: "0.2px",
          }}
        >
          {subtext}
        </div>
      )}
    </AbsoluteFill>
  );
};
