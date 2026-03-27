# Signal: Phase execution order now enforced with gates and dependency notes
- Date: 2026-03-26
- Rating: 8
- Category: improvement
- Source: session
- Observation: Tasklist previously had Phase 4 listed after Phase 3 but with no hard gates. Plan review revealed: 3D must precede 3E (vocabulary), 3E must precede 4A (heartbeat), 3D must precede 4D (autoresearch program can't be written without current-vs-ideal spec). Gates and dependency notes were added to tasklist and PRD.
- Implication: Correct build order is now documented: 3B(partial) → 3D → 3E → [Gate: AS1 + signals + heartbeat] → 4A → 4B → 4C → 4D → [Gate: AS2] → 5A → 5B. Do not start Phase 4 until the gate checklist passes.
- Context: Found during gap analysis of tasklist vs Miessler synthesis docs. Five gaps total were identified and addressed.
