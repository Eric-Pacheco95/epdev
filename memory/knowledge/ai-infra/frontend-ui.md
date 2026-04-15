# Frontend UI -- Graph Canvas and Cross-Platform Framework Selection

## Overview
Two independent frontend decisions with overlapping technology constraints: (1) interactive graph canvas for Jarvis brain-map using React Flow, and (2) cross-platform framework selection for future mobile/desktop expansion. Both inform the jarvis-app Sprint 3+ roadmap.

## Key Findings

### Graph Canvas for Brain Map (Article: 2026-03-27_jarvis-brain-map-graph-pm)
- No existing tool combines: markdown/git source-of-truth, interactive zoomable graph canvas, semantic node typing (TELOS -> Goals -> Projects -> ISC -> Tasks), AI gap-closing co-pilot, and write-back to source files. Jarvis brain-map is a confirmed greenfield build.
- React Flow confirmed: 35.6K GitHub stars, 4.59M weekly npm installs, MIT license. Contextual Zoom is a documented built-in pattern using useStore hook -- nodes read zoom level and render accordingly.
- Zoom-layer design: <0.2 = TELOS+Goals only; mid-zoom = Projects+ISC; full-zoom = Tasks+details. Prevents information overload at high altitude view.
- Git-native principle: all graph state maps back to markdown files; the canvas is a view layer, not the database. Write-back to source files is a first-class requirement, not an add-on.

### Cross-Platform Framework Selection (Article: 2026-03-28_cross-platform-framework-comparison)
- For TypeScript/React developer targeting iOS + Windows: React Native + Expo = lowest-friction path. Expo EAS enables cloud iOS builds with no Mac hardware required.
- Tauri v2 is best for Windows desktop: 1-10 MB installers vs Electron's 100-150 MB; <500ms startup; Rust backend with WebView frontend.
- React Native New Architecture (default since 0.76): 43% faster cold starts, 39% faster rendering, 26% lower memory vs old bridge. react-native-windows is Microsoft-maintained (used in Office products).
- Decision matrix: iOS priority -> React Native + Expo; Windows desktop priority -> Tauri v2; both targets -> React Native for mobile, Tauri for desktop (separate codebases accepted).

## Source Articles
- 2026-03-27_jarvis-brain-map-graph-pm.md (confidence: 8)
- 2026-03-28_cross-platform-framework-comparison.md (confidence: 9)

## Caveats
> LLM-flagged, unverified. Review during weekly consolidation.
- [ASSUMPTION] React Flow's Contextual Zoom pattern is described as "documented built-in" -- verify against current React Flow v12 docs; API surface changes between major versions.
- [ASSUMPTION] Expo EAS cloud iOS builds assume active Apple Developer Program enrollment ($99/yr) -- cost and account setup prerequisites not mentioned in the article.
- [ASSUMPTION] Brain-map article was truncated ("Zoom-layer design: <0.2 -> TELOS+Goals only;" -- cut off at mid-sentence); the full zoom-layer specification and additional UI patterns may be missing.
- [FALLACY] Appeal to authority: React Flow selection justified partly by star count and install volume -- popularity does not guarantee fitness for a specialized graph-PM use case with git write-back requirements.
- [FALLACY] False dichotomy: cross-platform article frames Tauri vs Electron as the primary binary choice; PWA + Capacitor is a viable third option for TypeScript-native teams and is not discussed.