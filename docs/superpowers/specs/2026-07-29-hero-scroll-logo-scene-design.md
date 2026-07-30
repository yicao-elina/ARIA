# Hero Scroll Logo Scene — Design Spec

**Date:** 2026-07-29
**Scope:** `docs/index.html` hero section (`#abstract`) on the ARIA project site.

## Problem

The ARIA logo (`docs/figures/ARIA-logo.svg`) used to appear as a watermark behind
the hero title but was removed because it read as muddy (multiply-blend
darkened the text it overlapped). The user wants the logo back, reimagined as
a scroll-driven scene:

1. On page load, the hero shows the title/subtitle/authors as it does today,
   flanked by two translucent, feather-edged **halves** of the ARIA logo
   bleeding off the left/right viewport edges — decorative, behind the text,
   never overlapping it.
2. As the user scrolls down through the hero, the two halves converge toward
   the center and merge/cross-fade into `docs/figures/ARIA-A.svg` (the single
   "A" mark), which settles at **small size, on the left**.
3. Simultaneously, the "What you'll explore in this article" `<details>` card
   (currently centered under the subtitle, collapsed) slides right and
   auto-expands, settling next to the now-small logo mark — matching the
   reference layout where the logo mark sits at left and an open, expanded
   info card sits at right.
4. Once fully settled, the pin releases and the settled logo+card scroll away
   normally with the rest of the page (confirmed with user — not a permanent
   sticky header; the existing floating pill nav already serves that role).

## Non-goals

- No changes to the pill header/nav, other sections, or the tour system.
- No new logo assets need drawing — both SVGs already exist and are raster
  images wrapped in an SVG `<filter>` (not editable vector paths), so all
  splitting/feathering/morphing is done with CSS masks/opacity, not by
  editing the SVG internals.
- Not a permanently-pinned mini header (ruled out by user Q&A below).

## Architecture

### Markup restructure (`docs/index.html`, `#abstract` section)

Wrap the current hero content in a new pinned scene:

```html
<section class="tile tile--parchment tile--hero" id="abstract">
  <div class="mesh mesh--hero" aria-hidden="true"></div>
  <div class="hero-scene" id="hero-scene">
    <div class="hero-scene__sticky">
      <div class="hero-scene__logo-half hero-scene__logo-half--left" aria-hidden="true"></div>
      <div class="hero-scene__logo-half hero-scene__logo-half--right" aria-hidden="true"></div>
      <img class="hero-scene__mark" src="assets/figures/ARIA-A.svg" alt="" aria-hidden="true" />
      <div class="tile__content">
        <!-- existing h1 / subtitle / authors / legend / date / cta, unchanged -->
        <div class="hero-lead">
          <p class="reveal">...</p>
          <details class="detail-toggle glass-card glass-card--compact reveal hero-scene__card" ...>
            <!-- unchanged contents -->
          </details>
        </div>
      </div>
    </div>
  </div>
</section>
```

- `.hero-scene` is the tall scroll track (`height: 220vh`).
- `.hero-scene__sticky` is `position: sticky; top: 0; height: 100vh` — pins
  its contents while the track scrolls underneath.
- The two `.hero-scene__logo-half` layers and `.hero-scene__mark` are purely
  decorative (`aria-hidden="true"`, no alt text needed) — the accessible
  logo already exists as the pill-header avatar (`alt="ARIA"`), so no
  branding information is lost to screen readers.
- The `<details>` element itself is untouched semantically (still native,
  still keyboard/AT operable) — only its position/size/open-state is
  animated via a CSS class + `open` attribute toggled by JS at the progress
  threshold, so behavior degrades gracefully with JS off.

### Split-logo halves (CSS)

Each half is a `background-image: url(assets/figures/ARIA-logo.svg)` block,
full logo image, clipped with a `mask-image` (not `clip-path`, so the feather
is soft):

- **Left half:** `mask-image: linear-gradient(to right, black 0%, black 42%, transparent 58%)` —
  hard-ish on the left, feathering out before the seam.
- **Right half:** mirrored gradient.
- Both additionally get a second mask layer (`mask-composite` intersect, or a
  radial gradient) feathering the *outer* edge toward the page margin, so
  they read as bleeding softly off-screen rather than cropped.
- `opacity: 0.16`, `filter: blur(0.5px) saturate(90%)` for the "frosted,
  behind-glass" look consistent with `glass.css`'s pearl/blur language.
- Positioned `position: absolute`, left half anchored near `left: -6%`,
  right half near `right: -6%`, vertically centered on the sticky viewport.

### Motion feel reference

User pointed to anthropic.com's scroll behavior as the target feel. That site
does not scroll-jack or hard-pin — it reveals content with smooth,
unhurried opacity + translateY (and occasional scale) transitions timed to
scroll position, generous durations (~600–900ms), soft cubic-bezier easing,
and staggered element-by-element reveal rather than everything moving at
once. This project already has that exact pattern half-built via
`reveal.js`'s `.reveal` class (IntersectionObserver-driven fade/slide-up).

Applying this to the hero scene means: the `--scene-progress`-driven
transforms (logo halves converging, card sliding/expanding) should use the
same unhurried, soft-eased quality — no snapping, no linear motion, no
speed that reads as "scroll-jacking." Concretely: transitions on the
interpolated properties use `transition: transform 400ms
cubic-bezier(.16,1,.3,1), opacity 400ms ease` (matching `glass-card`'s
existing easing curve) layered on top of the scroll-driven CSS variable, so
motion is smoothed rather than 1:1 tied to raw scroll deltas; and the
card's expand-on-settle reuses `reveal.js`'s existing fade/slide-up
treatment instead of a new one-off animation.

### Scroll progress engine (`assets/js/hero-scene.js`, new, deferred)

```js
// Pseudocode
function updateProgress() {
  const rect = heroScene.getBoundingClientRect();
  const trackable = rect.height - window.innerHeight;
  const progress = clamp(-rect.top / trackable, 0, 1);
  heroScene.style.setProperty('--scene-progress', progress);
  // Threshold-based <details> open/close toggle (avoid fighting user's
  // own manual toggle — only auto-open forward, never auto-close if the
  // user already interacted with the summary).
}
window.addEventListener('scroll', () => requestAnimationFrame(updateProgress), { passive: true });
```

- Sets exactly one CSS custom property per frame; all visual interpolation
  (`translateX`, `opacity`, `scale`, card `left`/`width`) happens in CSS via
  `calc(var(--scene-progress) * Npx)`, keeping the JS cheap and avoiding
  layout thrash.
- `prefers-reduced-motion: reduce` and `body.no-motion` (existing kill-switch
  convention in this codebase, see `glass.css`): skip the scroll listener
  entirely, set `--scene-progress: 1` once, collapse `.hero-scene` to
  `height: auto` (no pinned track) — user sees the settled end-state
  immediately, no scroll-jacking.
- If `assets/js/hero-scene.js` fails to load (matches this repo's existing
  "widgets no-op gracefully" pattern), CSS default (`--scene-progress: 0`
  via `:root` fallback, or simply the unsplit static hero) still renders a
  reasonable static hero — never a blank/broken state.

### Visual states across progress 0 → 1

| progress | logo halves | settled mark (`ARIA-A.svg`) | explore card |
|---|---|---|---|
| 0 | full opacity (0.16), at rest position (bleeding off edges) | opacity 0, small | centered under subtitle, collapsed (current default) |
| 0–0.6 | translateX toward center, opacity fading down | opacity ramps 0→1 | begins translating right |
| 0.6–1 | fully faded out | settled at final left position/size | fully right, `open` attribute set, expanded |
| 1 (pin releases) | — | static, in-flow | static, in-flow |

### CSS files

- New `assets/css/hero-scene.css` (keeps `sections.css` from growing past
  its current size — this repo already splits hero-only concerns into
  small dedicated files like `header-pill.css`, `mesh.css`).
- Reuses existing tokens from `design-tokens.css` / `glass.css` (blur values,
  `--pearl-glass`, ease curves) rather than inventing new ones.

### Title width adjustment

Per user request, if the split-logo halves' feathered edge would visually
brush the title text at common viewport widths, narrow `.tile--hero
.tile__content` max-width slightly (e.g. 880px → ~760px) rather than letting
text and logo overlap. Verified at implementation time against real
viewport widths, not assumed up front.

## Testing / verification plan

- No automated test framework covers this static HTML/CSS/JS site currently
  (grep confirms no JS test runner config) — verification is manual:
  1. Load the page, confirm hero renders correctly with JS disabled
     (DevTools → disable JavaScript) — static fallback state.
  2. Confirm `prefers-reduced-motion: reduce` emulation shows the settled
     end-state with no scroll-jacking.
  3. Scroll through the hero at normal speed and confirm: halves converge,
     no visual overlap with text at any progress value, card auto-expands
     once and doesn't fight manual open/close.
  4. Check narrow (390px), tablet (768px), and wide (1440px+) viewports.
  5. Confirm the pill header's existing scroll/reveal behavior is
     unaffected (no CSS/JS collisions with `reveal.js`, `header-*` files).

## Open questions resolved during brainstorming

- **End behavior after settling:** release into normal flow, not a
  permanent pinned mini-header (existing pill nav already covers that role).
