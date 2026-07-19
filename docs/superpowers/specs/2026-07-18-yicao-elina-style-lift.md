---
name: aria-yicao-elina-style-lift
description: Lift the ARIA paper website to the same visual and interactive quality as the yicao-elina personal site — glassmorphic cards with cursor spotlight + tilt, floating glass icon-pill header, mesh-gradient hero, mint accent system, spring easing, reveal-on-scroll. Keep Apple typography / spacing / tile rhythm as the base; add the glassmorphic personality on top without breaking the 7 existing interactive modules (KG Explorer, Main Table, Figure Viewer, PSP Cascade, Tunneling Demo, Tier Router, Robustness Slider).
---

# ARIA × yicao-elina Style Lift — Spec

## 1. Goal

Match the **visual quality, interactive feel, and material texture** of the
yicao-elina personal site (your own portfolio) while keeping the ARIA
paper website's scientific content, Apple typography, and 7 interactive
D3 modules fully functional.

Reference site: `~/Documents/yicao-elina` (branch `gh-pages`).
ARIA site: `ARIA/docs/`.

## 2. What makes yicao-elina distinctive (the "lift" target)

| Pillar | yicao-elina behaviour | Where it lives in reference |
|---|---|---|
| Floating glass icon-pill header | `position: fixed; top: 16px; border-radius: 9999px; backdrop-filter: blur(24px) saturate(180%)`; avatar + 5 icon buttons with tooltips; mobile collapse to hamburger | `assets/css/header.css` + `assets/js/header-tooltip.js` |
| Mesh-gradient hero | Two large radial-gradient blobs (`rgba(73,191,157,0.14)` mint + `rgba(245,185,66,0.12)` gold) `filter: blur(80–100px)`, 32–40s drift animation, `pointer-events: none`, scrolls with hero | `assets/css/hero.css` `.hero-mesh` |
| Glassmorphic cards | `background: rgba(255,255,255,0.55); border: 1px solid rgba(255,255,255,0.6); border-radius: 24px; backdrop-filter: blur(20-24px) saturate(180%); box-shadow: 0 8-12px 32px rgba(0,0,0,0.06-0.10)` | `assets/css/blog.css` `.glass-card` |
| Cursor spotlight | `::before` radial-gradient at `--mx/--my` (set by JS on `mousemove`), opacity 0 → 1 on hover, 220ms ease | `assets/css/blog.css` `.glass-card::before` + `assets/js/blog-spotlight.js` |
| Hover tilt | `transform: perspective(800px) rotateX(var(--tilt-y)) rotateY(var(--tilt-x))` driven by JS on `mousemove` (8px max rotation) | `assets/js/blog-tilt.js` (reused by `.tile`, `.glass-card`) |
| Mint accent system | Primary mint `#49bf9d` + bright `#49bf9d`; graphite `#4a5568`; ink `#141e2d`; pearl `#fafafc` | `assets/css/tokens.css` |
| Spring easing | `cubic-bezier(.34, 1.56, .64, 1)` for buttons/cards, `cubic-bezier(.16, 1, .3, 1)` for hero entrance | `tokens.css` `--ease-spring` |
| Staggered hero entrance | Personal card slides in from left-below with blur; tile grid flies in from below with per-tile `transition-delay` (180/250/320/390/460/530ms) | `assets/css/hero.css` |
| Reveal-on-scroll | Generic `.reveal` class observed by `IntersectionObserver`, then `.is-visible` adds `translate/scale/opacity` transitions | `assets/js/reveal-on-scroll.js` |
| Tooltip on header icons | `.ah-tooltip` absolutely positioned below, `opacity: 0 → 1`, spring `translateY(-4px → 0)` | `assets/js/header-tooltip.js` + `header.css` |
| Press state on everything | `transform: scale(0.95-0.97)` on `:active`/`:hover` for all CTAs (Apple rule) | `blog.css` `.btn-teal`, `hero.css` `.pc-cta` |
| Browser fallback | `@supports not ((backdrop-filter) or (-webkit-backdrop-filter))` swaps to opaque `rgba(255,255,255,0.92)` | `hero.css` |
| Reduced-motion safety | `@media (prefers-reduced-motion: reduce)` AND `body.no-motion` set by JS before paint | `hero.css`, `blog.css` |

## 3. What stays Apple (must not regress)

From `ARIA/docs/DESIGN-apple.md` and the current implementation:
- 17px body / 56px hero / 21px sub-nav / negative letter-spacing at display sizes
- Weight ladder 300/400/600 (no 500)
- 80px section padding, 24px card padding, 980/1440px content widths
- Apple breakpoints (419/640/834/1024/1068/1440)
- The "edge-to-edge tile" rhythm: alternating `tile--light` (white) and `tile--parchment` (#f5f5f7)
- The single product-shadow reserved for product imagery (now: paper figures)
- Tier colors: `--tier-1` #0066cc blue / `--tier-2` #c9930a gold / `--tier-3` #86868b grey — these are already aligned with mint + gold + grey, so the mint accent fits naturally

## 4. What ARIA has today (the "current state")

```
docs/
├── index.html                       (43 KB, Apple-only, no glass)
├── assets/
│   ├── css/  (10 files, Apple design tokens, no glass)
│   │   ├── design-tokens.css        ← Apple + tier tokens
│   │   ├── base.css
│   │   ├── navigation.css           ← single 52px frosted bar (top of page, not floating pill)
│   │   ├── sections.css
│   │   ├── components.css           ← tier cards, badges, callouts
│   │   ├── components-figures.css
│   │   ├── components-table.css
│   │   ├── interactive.css          ← D3 containers
│   │   ├── tier-themes.css
│   │   └── responsive.css
│   ├── js/  (9 files, D3 viz + nav)
│   │   ├── theme.js, main.js
│   │   ├── kg-explorer.js, psp-cascade.js, tunneling-demo.js
│   │   ├── tier-router.js, results-chart.js, robustness-slider.js
│   │   ├── figure-viewer.js, main-table.js
│   ├── data/  (4 files: aria_2d_kg_demo, benchmark_results, example_queries, main_table)
│   └── figures/  (13 PNG/SVG/PDF files)
```

The 7 D3 modules (KG Explorer, PSP Cascade, Tunneling Demo, Tier Router, Results Chart, Robustness Slider, Main Table) use the Apple `ARIA.theme.getColors()` token API — **keep that contract intact**.

## 5. Functional requirements (acceptance criteria)

### F1. Floating glass icon-pill header (replaces current top bar)
- Fixed, top 16px, horizontally centered, max-width ~720px
- Avatar circle (40px, mint 2px border) + 5–7 section icon buttons with SF Symbol-style SVGs
- `backdrop-filter: blur(24px) saturate(180%)`, `background: rgba(255,255,255,0.7)`, `border-radius: 9999px`, `box-shadow: 0 8px 32px rgba(20,30,45,0.08)`
- Each icon has a tooltip (`.ah-tooltip`) that appears on hover/focus with spring easing
- Active section icon gets `color: var(--mint)` and `aria-current="page"`
- Mobile (≤ 768px): collapse to avatar + 2 visible icons + "more" popover
- Maintains `header-offset: 96px` (top of `<main>` is 96px below viewport) — but since the pill is `position: fixed; top: 16px;` and short, we can reduce the body top offset to 16px + pill height (~64px) = ~80px

### F2. Mesh-gradient hero
- Two blobs: mint (top-left, 32s drift) + gold (bottom-right, 40s drift)
- `filter: blur(80-100px)`, `pointer-events: none`, scrolls with the section
- `body.no-motion` and `prefers-reduced-motion: reduce` both disable the drift and set opacity 1 immediately
- `@supports not (backdrop-filter)` falls back to `background: #fafafc`

### F3. Glassmorphic card recipe (new `.glass-card` base class)
- `background: rgba(255,255,255,0.55)`, `border: 1px solid rgba(255,255,255,0.6)`, `border-radius: 24px`, `backdrop-filter: blur(20px) saturate(180%)`, `box-shadow: 0 8px 32px rgba(0,0,0,0.06)`
- Cursor spotlight: `::before` radial-gradient at `--mx/--my` (360px circle, mint 0.18 → transparent 50%), opacity 0 → 1 on hover/focus-within
- Hover tilt: `perspective(800px) rotateX(var(--tilt-y)) rotateY(var(--tilt-x)) translateY(-6px)`, 220ms ease-out
- Fallback: `@supports not (backdrop-filter)` swaps to `rgba(255,255,255,0.92)`
- `prefers-reduced-motion: reduce` AND `body.no-motion` disable spotlight + tilt

### F4. Apply `.glass-card` to ARIA's existing cards
Re-skin, do not invent new layouts:
- KG Explorer stat tiles (the 4 `data-stat` cards)
- Main results table (wrap `.mt-table-host` card)
- Tier cards in the three-tier section
- Each paper figure block (in `#paper-figures`)
- Trace audit rows
- Callouts (`.callout`, `.key-insight`)

### F5. Reveal-on-scroll
- All section headings, paragraphs, `.glass-card`s, and figure blocks fade-and-rise on first intersection
- `IntersectionObserver` with `rootMargin: 0px 0px -10% 0px`, `threshold: 0.1`
- Add `.is-visible` to switch from `opacity: 0; translate: 0 24px` to settled
- Respect `prefers-reduced-motion: reduce` (jump straight to visible)

### F6. Mint accent system
- `--mint: #49bf9d`, `--mint-bright: #49bf9d`, `--mint-soft: rgba(73,191,157,0.10)`, `--ink-deep: #141e2d`, `--graphite: #4a5568`, `--pearl: #fafafc`
- Add to `design-tokens.css` (do not break existing `--apple-*` tokens — they coexist)
- Mint replaces Action Blue for: link hovers, primary CTA highlight on glass cards, focus rings on glass cards
- Action Blue is **kept** for: tier-1, the GitHub/Code links, the "View on GitHub" CTA, the data-table sort indicators (so scientific tier semantics don't get muddled with personal mint)

### F7. Spring easing as the default
- `--ease-spring: cubic-bezier(.34, 1.56, .64, 1)` for buttons, cards, tooltips
- `--ease-out-expo: cubic-bezier(.16, 1, .3, 1)` for hero entrance, reveal-on-scroll
- Update all `:hover`/`:active` transitions in `components.css` to use these

### F8. Staggered hero entrance
- Hero `<section>` first paints with `body.hero-ready` removed
- After paint, `main.js` adds `body.hero-ready` on next frame, which triggers the personal-card slide-in and tile grid fly-in
- Per-tile `transition-delay: 180/250/320/390/460/530ms`
- This is the **first section** of `index.html` (currently uses `tile--parchment tile--hero`)

### F9. Press state on every button
- Add `transform: scale(0.95)` on `:active` and `:hover` for: `.sub-nav__cta`, `.glass-card`, `.btn-teal` (or `.pc-cta`), `.fig-hotspot`, `.view-toggle__btn`
- 150–200ms ease

### F10. Lightbox stays (no change to figure-viewer.js, but re-skin the modal)
- `figure-viewer.js` keeps its data-full-src, Esc/backdrop-click-close, hotspot-jump behaviour
- Modal gets `.glass-card` treatment with mint accent ring

## 6. Non-goals (do NOT do these)

- Do not change the Apple design tokens (`--apple-primary`, `--tier-*`, typography scale, spacing scale). They coexist with the new mint accent.
- Do not add a second accent color. Mint is the only "personal" accent; Action Blue is the only "scientific" accent.
- Do not change the D3 visualization logic (PSP cascade topology, KG explorer graph data, etc.). Only the surrounding chrome (containers, hover states, entrance) gets the new skin.
- Do not change the data files (`*.json`). Same shapes, same values.
- Do not remove `aria.css.deprecated` (kept for reference per `PROGRESS.md`).
- Do not introduce a JS framework (React, Vue, etc.). Vanilla JS + D3 only.

## 7. File-level deltas (the contract)

**New files (5):**
- `docs/assets/css/glass.css` — `.glass-card`, `.glass-card--compact`, spotlight, tilt, fallback
- `docs/assets/css/mesh.css` — `.mesh`, `.mesh--hero`, `.mesh--page`, blob keyframes
- `docs/assets/css/header-pill.css` — `.app-header`, `.ah-avatar`, `.ah-icon`, `.ah-tooltip`, `.ah-popover`
- `docs/assets/js/glass-card.js` — spot + tilt + IntersectionObserver wiring (one class for all glass cards)
- `docs/assets/js/reveal.js` — generic IntersectionObserver reveal

**Modified files (8):**
- `docs/assets/css/design-tokens.css` — add `--mint`, `--mint-bright`, `--mint-soft`, `--ink-deep`, `--graphite`, `--pearl`, `--ease-spring`, `--ease-out-expo` (alongside existing tokens)
- `docs/assets/css/base.css` — set body bg to `--pearl`, link hover to mint, default font stays Inter
- `docs/assets/css/navigation.css` — keep the 52px frosted bar **as a sub-nav row** below the floating pill (both coexist), OR replace it entirely with the pill. Decision: replace (cleaner).
- `docs/assets/css/sections.css` — hero section uses `.mesh--hero` + `body.hero-ready` entrance; section headings use the spring reveal
- `docs/assets/css/components.css` — add `:active { transform: scale(0.95) }` to all buttons; replace tier card surface with `.glass-card--tier-N` variant
- `docs/assets/css/components-figures.css` — `.figure-block` re-skinned as `.glass-card`; hotspot pulse uses mint
- `docs/assets/css/components-table.css` — `.mt-table-host` re-skinned as `.glass-card`
- `docs/assets/css/tier-themes.css` — `.tier-badge` and `.confidence-*` keep Action Blue / gold / grey (no mint contamination on tier semantics)
- `docs/assets/js/main.js` — call `GlassCards.init()` after D3 modules; add `body.hero-ready` toggle after first paint; wire `Reveal.init()` for headings
- `docs/index.html` — replace `sub-nav-frosted` with the new `.app-header` pill; add `mesh` div inside `<section id="hero">` and inside the `<body>` as page-level mesh; add `class="reveal"` to section headings and `class="glass-card"` to cards

**Unchanged files (7 — the 7 D3 modules + 4 data files + the new figure-viewer.js, theme.js, aria.css.deprecated):**
- `theme.js`, `figure-viewer.js`, `psp-cascade.js`, `tunneling-demo.js`, `kg-explorer.js`, `tier-router.js`, `results-chart.js`, `robustness-slider.js`, `main-table.js`
- `aria_2d_kg_demo.json`, `benchmark_results.json`, `example_queries.json`, `main_table.json`
- `aria.css.deprecated`
- `responsive.css` (only minor breakpoint adjustments if needed; no major changes)

## 8. Verification

After implementation, the following must all pass (using the same Node.js VM-based smoke test recipe from `PROGRESS.md`):

1. **Static check**: 12 JS files parse, 12 CSS files exist, 4 data files exist, 13 figure files exist
2. **Token contract**: every D3 module can still call `ARIA.theme.getColors()` and get a value (mint + tier colors both present)
3. **Glass card contract**: every `<article class="glass-card">` and `class="* glass-card"` instance has a `--mx/--my` updated by `mousemove` (or stays at `50% 50%` default for keyboard)
4. **Header pill**: 5+ `.ah-icon` elements, each with a `.ah-tooltip` child
5. **Mesh**: `.mesh` exists in hero section, both `::before` and `::after` blobs present
6. **Reveal**: every `class="reveal"` element has `IntersectionObserver` attached
7. **Reduced motion**: `body.no-motion` set if `matchMedia('(prefers-reduced-motion: reduce)').matches` at boot
8. **Browser fallback**: `@supports not (backdrop-filter)` block in every CSS file that uses `backdrop-filter`
9. **Visual screenshot**: render the page headlessly (via the same ImageMagick / playwright-via-skill recipe from `PROGRESS.md`) and produce `docs/figures/overviews/glass_lift_*.png` for visual diff

## 9. Roll-out strategy

This is a multi-step change. Implementation order matters because each step should be visually verifiable in isolation:

1. **Tokens & base** — add mint tokens + spring easing + body bg → verify the page still looks like Apple
2. **Glass-card CSS + JS** — add the recipe + cursor spotlight + tilt → apply to ONE card (the KG Explorer stats) to verify the effect, then propagate
3. **Floating pill header** — replace the top bar → verify scroll behavior, mobile collapse, tooltips
4. **Mesh hero** — add mesh div to hero section → verify drift, reduced-motion fallback
5. **Reveal-on-scroll** — wire IntersectionObserver → verify entrance + reduced-motion
6. **Apply glass-card to the remaining 5 surfaces** (table, tier cards, paper figures, trace audit, callouts) → verify each in isolation
7. **Final QA** — full smoke test + visual screenshots + reduced-motion pass

## 10. Known caveats carried over from `PROGRESS.md`

- Local sandbox cannot reach `127.0.0.1:8080` (`Operation not permitted`). Verification uses static file inspection + Node.js VM + ImageMagick compositing. Site is fully functional on the user's machine.
- `aria.css.deprecated` is kept for reference, not linked.
- OneDrive sync sometimes blocks file reads; use absolute paths and retry on `ETIMEDOUT`.
