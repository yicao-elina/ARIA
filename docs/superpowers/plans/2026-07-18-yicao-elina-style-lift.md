# ARIA × yicao-elina Style Lift — Implementation Plan

**Branch:** working tree (no commit yet — user hasn't asked for one)
**Spec:** `docs/superpowers/specs/2026-07-18-yicao-elina-style-lift.md`
**Started:** 2026-07-18
**Reference site:** `~/Documents/yicao-elina`

## Task status

| # | Task | Status | Owner | Files |
|---|------|--------|-------|-------|
| 1 | Add mint + spring tokens to design-tokens.css | pending | subagent A | `docs/assets/css/design-tokens.css` |
| 2 | Wire mint into base.css (body bg, link hover) | pending | subagent A | `docs/assets/css/base.css` |
| 3 | Create glass-card CSS (`.glass-card`, spotlight, tilt, fallback) | pending | subagent B | `docs/assets/css/glass.css` (new) |
| 4 | Create glass-card JS (spot + tilt + observer wiring) | pending | subagent B | `docs/assets/js/glass-card.js` (new) |
| 5 | Create floating pill header CSS | pending | subagent C | `docs/assets/css/header-pill.css` (new) |
| 6 | Create header-tooltip JS | pending | subagent C | `docs/assets/js/header-tooltip.js` (new) |
| 7 | Create mesh gradient CSS | pending | subagent D | `docs/assets/css/mesh.css` (new) |
| 8 | Create reveal-on-scroll JS | pending | subagent D | `docs/assets/js/reveal.js` (new) |
| 9 | Replace top nav in index.html with the pill | pending | subagent E (after 5,6) | `docs/index.html` |
| 10 | Add hero mesh to index.html | pending | subagent E (after 7) | `docs/index.html` |
| 11 | Apply `.glass-card` to KG Explorer stats | pending | subagent E (after 3,4) | `docs/index.html`, `docs/assets/css/interactive.css` |
| 12 | Apply `.glass-card` to main results table | pending | subagent E (after 3,4) | `docs/index.html`, `docs/assets/css/components-table.css` |
| 13 | Apply `.glass-card` to tier cards | pending | subagent E (after 3,4) | `docs/index.html`, `docs/assets/css/components.css` |
| 14 | Apply `.glass-card` to paper figures | pending | subagent E (after 3,4) | `docs/index.html`, `docs/assets/css/components-figures.css` |
| 15 | Apply `.glass-card` to trace audit + callouts | pending | subagent E (after 3,4) | `docs/index.html`, `docs/assets/css/components.css` |
| 16 | Wire hero entrance + reveal in main.js | pending | subagent F (after 3,4,5,6,7,8) | `docs/assets/js/main.js` |
| 17 | Add `:active { scale(0.95) }` to all CTAs | pending | subagent A (after 1) | `docs/assets/css/components.css`, `docs/assets/css/navigation.css` |
| 18 | Reduced-motion pass across all new CSS | pending | each subagent A–E | every new file |
| 19 | Final smoke test + visual screenshots | pending | orchestrator (after 1–18) | `/tmp/aria_lift_*.js` + `docs/figures/overviews/glass_lift_*.png` |

## Dependency graph

```
1 (tokens) → 2 (base) → 17 (press states) → ─┐
3 (glass CSS)  ─┐                            ├─→ 9, 10, 11, 12, 13, 14, 15 (HTML re-skin) → 16 (main.js wire) → 19 (smoke test)
4 (glass JS)   ─┤                            │
5 (header CSS) ─┼─→ 6 (header JS) ──────────→│
7 (mesh CSS)   ─┼─→ 8 (reveal JS)  ─────────→│
                                                │
18 (a11y) runs in parallel with each subagent  ─┘
```

Subagents A, B, C, D can all run in parallel. Subagent E (HTML re-skin) and F (main.js wire) must wait for A–D. Smoke test (19) is sequential after everything.

## Cross-cutting concerns

- **Token compatibility**: A, B, C, D, E, F all reference `--mint`, `--ease-spring`, etc. — these MUST exist before anything else. Task 1 is the only true dependency.
- **D3 contract**: A, B, F must preserve `ARIA.theme.getColors()`. The mint + tier colors both go in `theme.js`'s source map.
- **Backdrop-filter fallback**: every CSS that uses `backdrop-filter` must have the `@supports not (...)` block.
- **Reduced motion**: every new CSS file and JS init must respect `prefers-reduced-motion: reduce` AND `body.no-motion`.
- **OneDrive sync**: use absolute paths, retry on `ETIMEDOUT`, do not `git add -A`.
- **D3 modules are read-only**: PSP cascade, KG explorer, tier router, results chart, robustness slider, tunneling demo, main table — their JS files are NOT touched. Only the containers they render into are re-skinned.

## Commit strategy

User did not ask for a commit. Work stays in working tree until they say "commit". When they do, one commit per task batch:

```
feat(site): add mint accent + spring easing tokens       (Task 1, 2, 17)
feat(site): add glass-card recipe (CSS + JS)              (Task 3, 4, 11, 12, 13, 14, 15)
feat(site): add floating glass icon-pill header          (Task 5, 6, 9)
feat(site): add mesh-gradient hero + page backdrop        (Task 7, 10)
feat(site): add reveal-on-scroll                          (Task 8, 16)
test(site): smoke test + visual screenshots              (Task 19)
```

## Verification

See spec section 8. Three checks per subagent before claiming done:
1. Their files parse (CSS has matched braces, JS passes `new Function('window','document', src)`)
2. Their selectors are in the HTML where the spec says
3. The reduced-motion + `@supports` blocks are present

Final QA (Task 19) is the orchestrator's smoke test (see `PROGRESS.md` end).
