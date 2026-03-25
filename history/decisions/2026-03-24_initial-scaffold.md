# Decision: Initial Project Scaffold Architecture

- **Date**: 2026-03-24
- **Context**: Setting up the epdev Jarvis AI brain from scratch. Evaluated Daniel Miessler's PAI ecosystem (PAI v4.0.3, Fabric, Telos, TheAlgorithm, Ladder, Daemon, Substrate, SecLists) for integration.
- **Options Considered**:
  1. **Clone PAI directly** — Use PAI v4.0.3 as-is, customize USER/ directory. Pros: fastest start, proven architecture. Cons: PAI doesn't officially support Windows yet, heavy macOS/Linux assumptions in hooks (TypeScript/Bun), some features (voice, ntfy) not immediately needed.
  2. **Build from scratch inspired by PAI** — Cherry-pick PAI's best concepts (memory tiers, hook lifecycle, TELOS, Algorithm, agent system) into a custom scaffold optimized for our needs. Pros: Windows-compatible from day 1, no dead weight, full control. Cons: more upfront work.
  3. **Hybrid** — Use PAI's conceptual architecture but build custom scaffold, with Fabric installed as an external tool. Reference PAI/Telos/TheAlgorithm/Ladder for patterns.
- **Decision**: Option 3 (Hybrid)
- **Rationale**: PAI's Windows support is "not yet supported" per PLATFORM.md. The TypeScript/Bun hooks assume Unix tooling. Building a custom scaffold lets us match PAI's architecture while ensuring Windows compatibility. Fabric installed separately as a CLI tool. Reference repos cloned to /tmp for pattern mining.
- **Reversibility**: Easy — can always migrate to full PAI later if Windows support lands
- **Review Date**: 2026-04-07
