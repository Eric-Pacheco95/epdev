/**
 * Root.tsx — Remotion composition aggregator.
 *
 * Each demo project lives in its own file under src/compositions/.
 * To add a new demo: create src/compositions/<project>.tsx, export a
 * *Compositions React component, and register it here.
 *
 * Project files:
 *   src/compositions/pai-cli-demo.tsx   — PAI "create-demo-video" meta-demo (10 scenes)
 *   src/compositions/td-keynote.tsx     — TD Bank Innovation Week 2026 keynote (5 compositions)
 */

import React from "react";
import { PAICliDemoCompositions } from "./compositions/pai-cli-demo";
import { TDKeynoteCompositions } from "./compositions/td-keynote";
import { WorkbenchPhase3Compositions } from "./compositions/workbench-phase3";

export const RemotionRoot: React.FC = () => (
  <>
    <PAICliDemoCompositions />
    <TDKeynoteCompositions />
    <WorkbenchPhase3Compositions />
  </>
);
