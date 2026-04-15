# Harness Engineering and Reliability Architecture

## Overview
Research on making AI agent pipelines reliable through deterministic scaffolding. Covers Claude Code harness architecture (CLAUDE.md vs hooks), Karpathy's reliability math, and PAI v4.0.3 architectural patterns that Jarvis should adopt. Core insight: reliability comes from deterministic rails, not per-step model improvement.

## Key Findings

### Reliability Architecture
- Karpathy's "March of Nines": 5-step chain at 95% per-step = 77% end-to-end; 10-step = 60%; harnesses solve this by inserting deterministic validation gates between LLM steps
- CLAUDE.md is advisory (~80% reliable) -- suitable for conventions, guidance, style; hooks are deterministic (100%) -- anything that must fire without exception (security blocks, audit logging, formatting) belongs in hooks
- Skills encode repeatable workflows; hooks enforce invariants; CLAUDE.md provides context; each layer has a distinct and non-interchangeable reliability contract

### PAI v4 Architectural Gap Analysis
- PAI v4.0.3 stats: 63 skills, 21 hooks, 338 workflows, 202 tips, Algorithm v3.6.0; Jarvis shares the same DNA (7-phase Algorithm, TELOS, ISC, 3-tier memory, constitutional security) but diverges on execution model
- Highest-value gap: CLI-first architecture -- PAI builds deterministic Python CLI tools with --flags first, then wraps with AI; Jarvis is currently prompt-first (inverted priority)
- Steering rule "does this step require intelligence? No -> Python script" exists in Jarvis but is not consistently applied; operationalizing this is the actionable gap, not adding new capabilities

### Practical Actions
- Audit existing skills: identify steps that are deterministic (file reads, format checks, grep validation) and extract to standalone CLI scripts
- Hook coverage audit: enumerate all "must happen" behaviors currently living in CLAUDE.md and migrate to PreToolUse/PostToolUse hooks
- PAI's 21 hooks vs Jarvis current hook count -- gap is a concrete metric to close incrementally

## Source Articles
- 2026-03-30_harness-engineering.md (confidence: 9)
- 2026-03-30_pai-v4-jarvis-comparison.md (confidence: 9)

## Caveats
> LLM-flagged, unverified. Review during weekly consolidation.
- [ASSUMPTION] Karpathy's 95% per-step figure is illustrative, not empirically measured for Claude Code specifically; actual per-step reliability varies by task type, model version, and prompt quality
- [ASSUMPTION] PAI's 338 workflows are assumed to be high-quality production patterns; survivorship bias -- only successful patterns make it into a published framework; failure modes and abandoned patterns are not represented
- [FALLACY] Appeal to authority -- "PAI has 21 hooks therefore Jarvis needs similar hook coverage" conflates quantity with invariant coverage; what matters is which specific invariants are enforced, not the count
- [FALLACY] False dichotomy -- "CLAUDE.md is advisory, hooks are deterministic" understates that hooks can also be bypassed (--no-verify, permission denial, hook errors); the reliability gap is real but the 80%/100% framing is not absolute