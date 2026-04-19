# Frontend & UI — Steering Rules

> Behavioral constraints for frontend/UI work (jarvis-app and any future browser-facing projects). Loaded contextually by frontend-related skills and jarvis-app PRDs rather than universally via `CLAUDE.md`. Created 2026-04-19 during synthesis 2026-04-19f.

## CSS & Tailwind

### Tailwind v4 — unlayered bare selectors in `globals.css` are utility killers

For Tailwind v4 projects, any bare selector in `globals.css` that targets `*`, `html`, `body`, or element types (e.g. `div`, `p`, `h1`) AND lives outside an `@layer` block beats every layered Tailwind utility regardless of specificity — per the CSS Cascade Layers spec, unlayered rules win against ALL layered rules. Tailwind v4 places utilities inside `@layer utilities`, so an unlayered `* { margin: 0 }` silently nullifies every `.mx-*`, `.px-*`, `.gap-*` site-wide.

**Diagnostic fingerprint:** asymmetric breakage where `flex` / `font-bold` / color utilities work but spacing utilities (`px-*`, `mx-*`, `gap-*`, grid spacing) silently fail.

**How to apply:** (1) audit `globals.css` at project init — any bare selector outside `@layer` is suspicious; (2) when Tailwind utilities "don't apply" but the class IS in the generated CSS, look for unlayered rules BEFORE investigating config/content-scan; (3) wrap suspect rules in `@layer base { ... }` or delete them if Tailwind preflight already covers the intent. This belongs in the Phase B B4 ESLint+grep CSS drift gate rule set.

**Reference incident:** 2026-04-19 — `* { margin: 0; padding: 0; box-sizing: border-box }` as an unlayered rule in jarvis-app `globals.css` broke every Tailwind spacing utility site-wide for weeks. Fix: wrap in `@layer base` (commit `de88799`). The rule was also redundant with Tailwind's own preflight (which is in `@layer base`).

## Loaded by

- `memory/work/phase-b-prd.md` — B4 CSS Drift Gate ESLint rules
- jarvis-app frontend PRDs (future)
