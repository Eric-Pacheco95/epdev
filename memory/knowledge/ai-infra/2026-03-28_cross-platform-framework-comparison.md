---
domain: ai-infra
source: /research (backfill)
date: 2026-03-28
topic: Cross-Platform Framework Comparison — React Native, Tauri, Electron, Flutter
confidence: 9
source_files:
  - memory/work/frontend-research/research_brief.md
tags: [react-native, tauri, expo, cross-platform, ios, windows, frontend]
---

## Key Findings
- For a TypeScript/React developer targeting iOS and Windows: **React Native + Expo** is lowest-friction for both App Stores (Expo EAS enables cloud iOS builds — no Mac required); **Tauri v2** is best for Windows desktop (1–10 MB installers vs Electron's 100–150 MB, <500ms startup)
- React Native New Architecture (default since 0.76): 43% faster cold starts, 39% faster rendering, 26% lower memory vs old bridge; `react-native-windows` is Microsoft-maintained (used in Office modernization)
- Tauri v2 (stable Oct 2024) added iOS/Android support but the mobile plugin ecosystem is only 15 months old and thin; iOS requires Xcode — no cloud build equivalent to Expo EAS
- Electron is eliminated for cross-platform use cases — no iOS/mobile story; Flutter requires full Dart language pivot (high cost for solo TypeScript developer); .NET MAUI requires C# (near-zero transfer from TypeScript)
- PWA is the zero-migration option — good on Windows via Edge/Microsoft Store (PWABuilder), but iOS has persistent limitations (no auto-install prompt, limited push notifications, App Store Guideline 4.2 rejection risk)

## Context
The research covered 35+ sources across three parallel research agents. The current React/Next.js/TypeScript stack is well-positioned — no wrong choice was made. Path A (iOS-first): React Native + Expo. Path B (Windows desktop-first, light mobile): Tauri v2 for desktop, separate React Native/Expo for iOS if App Store is needed. Hybrid two-codebase architecture is production-validated.

## Open Questions
- Does the Jarvis dashboard need iOS App Store presence, or is Windows + local dev server sufficient?
- What is the actual react-native-windows compatibility status for the key dashboard dependencies?
- When does Tauri v2's mobile plugin ecosystem become mature enough to replace React Native for mobile?
