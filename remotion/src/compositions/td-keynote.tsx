/**
 * td-keynote.tsx — TD Bank Innovation Week 2026 keynote compositions.
 *
 * Registered in Root.tsx as <TDKeynoteCompositions />.
 * Contains: 4 title cards + 1 Claude.ai UI mockup.
 */

import React from "react";
import { Composition } from "remotion";
import { TitleCard, TitleCardProps } from "../scenes/TitleCard";
import { UIMockup, UIMockupProps } from "../scenes/UIMockup";
import { FPS, WIDTH, HEIGHT } from "../config";

export const TDKeynoteCompositions: React.FC = () => (
  <>
    <Composition
      id="td-keynote-title-01"
      component={TitleCard as any}
      durationInFrames={8 * FPS}
      fps={FPS}
      width={WIDTH}
      height={HEIGHT}
      defaultProps={{ headline: "What if every AI workflow\nran in one command?", subtext: "", style: "dark-hook" }}
    />
    <Composition
      id="td-keynote-title-03"
      component={TitleCard as any}
      durationInFrames={7 * FPS}
      fps={FPS}
      width={WIDTH}
      height={HEIGHT}
      defaultProps={{ headline: "Same methodology.\nTD laptop. No installs.", subtext: "Standard Claude Enterprise — runnable today", style: "dark-transition" }}
    />
    <Composition
      id="td-keynote-title-06"
      component={TitleCard as any}
      durationInFrames={10 * FPS}
      fps={FPS}
      width={WIDTH}
      height={HEIGHT}
      defaultProps={{ headline: "47 skills.\nYour team's best practice —\ncaptured once, used forever.", subtext: "Attrition risk drops. Onboarding compresses. Output lifts.", style: "dark-statement" }}
    />
    <Composition
      id="td-keynote-title-07"
      component={TitleCard as any}
      durationInFrames={10 * FPS}
      fps={FPS}
      width={WIDTH}
      height={HEIGHT}
      defaultProps={{ headline: "90 days.\nOne team.\nProve it.", subtext: "TD Innovation Week 2026", style: "dark-close" }}
    />

    <Composition
      id="td-keynote-ui-04"
      component={UIMockup as any}
      durationInFrames={60 * FPS}
      fps={FPS}
      width={WIDTH}
      height={HEIGHT}
      defaultProps={{
        interface: "claude-ai-browser",
        conversation: [
          {
            role: "user",
            text:
              "You are a TD Business Analyst assistant.\n\n" +
              "Meeting: Vendor Identity Verification Review — 2026-04-10\n" +
              "Attendees: Sarah M (BA), David K (Risk), Priya R (Compliance)\n\n" +
              "Vendor returns customer DOB and full name in error payload on failed " +
              "identity checks — flagged as potential PIPEDA risk by Priya.\n" +
              "Decision: Pause vendor API expansion until compliance sign-off.\n" +
              "Action owner: Priya R — submit to legal by April 18.\n\n" +
              "/meeting-notes",
          },
          {
            role: "assistant",
            streaming: true,
            text_blocks: [
              "## Meeting Notes — Vendor Identity Verification Review\n\n",
              "**Date:** 2026-04-10 | **Attendees:** Sarah M, David K, Priya R\n\n",
              "---\n\n",
              "### Decisions\n",
              "- Pause vendor API expansion pending compliance sign-off\n\n",
              "### Action Items\n",
              "| Owner | Action | Due |\n",
              "|-------|--------|-----|\n",
              "| Priya R | Submit vendor DOB/name exposure to legal for PIPEDA review | 2026-04-18 |\n",
              "| Sarah M | Block sprint work on vendor API expansion | Immediate |\n\n",
              "### Risk Register\n",
              "| Risk | Severity | Flag |\n",
              "|------|----------|------|\n",
              "| Vendor returning PII in error payloads | HIGH | **[REGULATORY: PIPEDA s.7]** |\n",
              "| Legal review delay slips sprint 3 | MEDIUM | Track |\n\n",
              "### Executive Summary\n",
              "Vendor identity check returns customer PII in error payload — " +
                "legal review required before expansion. Sprint 3 at risk if review exceeds 8 days.\n",
            ],
            highlight_text: "[REGULATORY: PIPEDA s.7]",
          },
        ],
      }}
    />
  </>
);
