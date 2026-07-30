# Hero Scroll Logo Scene Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Bring the ARIA logo back onto the hero section as two translucent, feather-edged halves that converge into the `ARIA-A.svg` mark as the user scrolls, while the "What you'll explore" card slides right and expands to settle next to it.

**Architecture:** A new pinned scroll track (`.hero-scene`, `height: 220vh`, `position: sticky` inner viewport) wraps the existing hero content. A single JS-set CSS custom property (`--scene-progress`, 0→1) drives all visual interpolation via `calc()` in CSS — the JS never touches layout/style properties directly, only the one variable. `prefers-reduced-motion` and `body.no-motion` skip the scroll listener and render the settled end-state statically; if the JS file fails to load entirely, the CSS default (`--scene-progress: 0`) degrades to a static (harmless, slightly tall) hero showing the rest-state artwork.

**Tech Stack:** Plain HTML/CSS/JS (no build step, no framework) — matches the rest of `docs/`. No test runner exists for this static site; verification is manual (load in browser, check computed styles, scroll-check at multiple viewports).

## Global Constraints

- Decorative logo layers (`.hero-scene__logo-half`, `.hero-scene__mark`) are `aria-hidden="true"` with no `alt` text — the accessible logo name already exists via the pill-header avatar (`alt="ARIA"`), so this is a decoration, not new content.
- The `<details class="detail-toggle">` "What you'll explore" element stays a native `<details>`/`<summary>` — never replaced with a div+JS toggle — so keyboard/AT behavior is unaffected.
- All progress-driven motion uses `cubic-bezier(.16, 1, .3, 1)` / `ease`, matching the existing easing already used by `.glass-card` in `glass.css` — no new easing curve invented.
- JS sets exactly one CSS custom property per animation frame (`--scene-progress`); no direct style writes to transform/opacity/width from JS (keeps it cheap, keeps CSS as the single source of truth for visual state).
- Auto-opening the `<details>` card must never override a user's own manual toggle — track manual interaction via a `click` listener on the `<summary>`, not the `toggle` event (setting `.open` programmatically also fires `toggle`, so `click` is the only reliable "user did this" signal).
- New files only: `assets/css/hero-scene.css`, `assets/js/hero-scene.js`. No existing CSS/JS files are rewritten wholesale — only `docs/index.html` and (possibly, Task 5) one line of `assets/css/sections.css` are edited in place.

---

### Task 1: Restructure hero markup + base (rest-state) CSS

**Files:**
- Modify: `docs/index.html:8-21` (add stylesheet link), `docs/index.html:84-126` (restructure hero markup)
- Create: `docs/assets/css/hero-scene.css`

**Interfaces:**
- Produces: `.hero-scene`, `.hero-scene__sticky`, `.hero-scene__logo-half--left`, `.hero-scene__logo-half--right`, `.hero-scene__mark`, `.hero-scene__card` CSS classes and the `--scene-progress` custom property (default `0`, consumed by Tasks 3–4).
- Consumes: nothing (first task).

- [ ] **Step 1: Add the new stylesheet link**

In `docs/index.html`, right after the `mesh.css` link (line 21):

```html
  <link rel="stylesheet" href="assets/css/mesh.css" />
  <link rel="stylesheet" href="assets/css/hero-scene.css" />
```

- [ ] **Step 2: Restructure the hero section markup**

Replace the hero section (currently `docs/index.html:85-126`, from `<section class="tile tile--parchment tile--hero" id="abstract">` through its closing `</section>`) with:

```html
<section class="tile tile--parchment tile--hero" id="abstract">
  <div class="mesh mesh--hero" aria-hidden="true"></div>
  <div class="hero-scene" id="hero-scene">
    <div class="hero-scene__sticky">
      <div class="hero-scene__logo-half hero-scene__logo-half--left" aria-hidden="true"></div>
      <div class="hero-scene__logo-half hero-scene__logo-half--right" aria-hidden="true"></div>
      <img class="hero-scene__mark" src="assets/figures/ARIA-A.svg" alt="" aria-hidden="true" />
      <div class="tile__content">
        <h1 class="hero-title reveal">ARIA: A Causal-Aware Framework for Rescuing LLM Reasoning in Materials Discovery</h1>
        <p class="hero-subtitle reveal">Gating knowledge on causal completeness to prevent <em>contextual tunneling</em> in LLMs</p>
        <p class="hero-authors reveal">
          <a class="term-tip term-tip--below" href="https://yicao-elina.github.io/yicao-elina/" target="_blank" rel="noopener" data-tip="Chemical and Biomolecular Engineering, Johns Hopkins University · ycao73@jh.edu">Yi Cao<sup class="byline-mark byline-mark--dagger">†</sup></a>,
          <a class="term-tip term-tip--below" href="https://scholar.google.com/citations?user=RPw7AlUAAAAJ&amp;hl=zh-CN" target="_blank" rel="noopener" data-tip="Computer Science, Johns Hopkins University · lwang240@jh.edu">Liaoyaqi Wang<sup class="byline-mark byline-mark--dagger">†</sup></a>,
          <a class="term-tip term-tip--below" href="http://www.jienengchen.com/" target="_blank" rel="noopener" data-tip="Computer Science, Johns Hopkins University · jchen293@jhu.edu">Jieneng Chen</a>,
          <a class="term-tip term-tip--below" href="https://www.cs.jhu.edu/~vandurme/" target="_blank" rel="noopener" data-tip="Computer Science, Johns Hopkins University · vandurme@jhu.edu">Benjamin Van Durme<sup class="byline-mark byline-mark--star">*</sup></a>,
          <a class="term-tip term-tip--below" href="https://www.cs.jhu.edu/~ayuille/" target="_blank" rel="noopener" data-tip="Computer Science, Johns Hopkins University · ayuille1@jhu.edu">Alan Yuille<sup class="byline-mark byline-mark--star">*</sup></a>,
          <a class="term-tip term-tip--below" href="https://engineering.jhu.edu/chembe/faculty/paulette-clancy/" target="_blank" rel="noopener" data-tip="Chemical and Biomolecular Engineering, Johns Hopkins University · pclancy3@jhu.edu">Paulette Clancy<sup class="byline-mark byline-mark--star">*</sup></a>
        </p>
        <p class="hero-authors-legend reveal">
          <span class="byline-legend-item"><span class="byline-mark byline-mark--star">*</span> Corresponding author</span>
          <span class="byline-legend-sep" aria-hidden="true">·</span>
          <span class="byline-legend-item"><span class="byline-mark byline-mark--dagger">†</span> Equal contribution</span>
        </p>
        <p class="hero-date reveal">KDD 2026 · AI for Sciences Track</p>
        <div class="hero-cta reveal">
          <a href="https://github.com/yicao-elina/aria" class="sub-nav__cta" target="_blank" rel="noopener">Code &amp; Data</a>
          <a href="#problem" class="toggle-btn">Explore ↓</a>
          <button type="button" id="tour-start-btn" class="toggle-btn tour-cta">Take a Tour</button>
        </div>
        <div class="hero-lead">
          <p class="reveal">
            Naively augmenting LLMs with knowledge graph evidence can <em>degrade</em> performance—over-anchoring on correct-but-incomplete evidence. <strong>ARIA</strong> fixes this with a three-tier cascade that gates evidence on <em>causal completeness</em>.
          </p>
          <details class="detail-toggle glass-card glass-card--compact reveal hero-scene__card">
            <summary>What you'll explore in this article</summary>
            <div class="detail-toggle__body">
              <ul>
                <li>Why adding knowledge can hurt, and the failure mode we call <em>contextual tunneling</em></li>
                <li>The Processing–Structure–Property (PSP) hierarchy and what makes a causal chain <em>complete</em></li>
                <li>How ARIA's three-tier cascade decides <em>when</em> to use retrieved evidence</li>
                <li>An auditable causal trace you can inspect end-to-end</li>
              </ul>
            </div>
          </details>
        </div>
      </div>
    </div>
  </div>
</section>
```

(This is identical to the current hero content, just wrapped in `.hero-scene` / `.hero-scene__sticky`, with the three decorative layers added and `hero-scene__card` appended to the `<details>` class list.)

- [ ] **Step 3: Create `docs/assets/css/hero-scene.css` with rest-state styles**

```css
/* ==========================================================================
   hero-scene.css
   Scroll-driven hero logo scene: two feathered logo halves converge into
   the ARIA-A mark as the user scrolls past the hero, while the "What
   you'll explore" card slides right and expands. All motion is driven by
   the single --scene-progress custom property (0 at rest, 1 fully
   settled), set by assets/js/hero-scene.js. Without that script (or with
   prefers-reduced-motion), --scene-progress stays at its default (0),
   which is a valid, harmless static rest state — never broken.
   ========================================================================== */

.hero-scene {
  position: relative;
  height: 220vh;
  --scene-progress: 0;
}

.hero-scene__sticky {
  position: sticky;
  top: 0;
  height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  overflow: hidden;
}

/* ---------- Split logo halves ----------
   Each half shows one side of the same ARIA-logo.svg: the element is
   half the logo's natural width, background-size is 200% of the
   element's own width (= the logo's full natural width), and
   background-position picks which side is visible. */

.hero-scene__logo-half {
  position: absolute;
  top: 50%;
  width: 46vw;
  max-width: 560px;
  /* Half-image aspect ratio, NOT the full logo's ratio: this box shows
     only half the logo (via background-size: 200% below), so its own
     aspect ratio must be half of the full image's 296.25:139.5 ratio —
     i.e. 148.125:139.5 — or the rendered image stretches ~2x. */
  aspect-ratio: 148.125 / 139.5;
  background-image: url("../figures/ARIA-logo.svg");
  background-size: 200% 100%;
  background-repeat: no-repeat;
  pointer-events: none;
  /* top: 50% alone only aligns this element's top edge to the container
     midline (absolutely-positioned elements ignore the flex centering
     on .hero-scene__sticky) — translateY(-50%) is required to actually
     center it. */
  transform: translateY(-50%);
}

.hero-scene__logo-half--left {
  left: -8%;
  background-position: 0% 50%;
  -webkit-mask-image: linear-gradient(to right, transparent 0%, black 12%, black 44%, transparent 60%);
  mask-image: linear-gradient(to right, transparent 0%, black 12%, black 44%, transparent 60%);
}

.hero-scene__logo-half--right {
  right: -8%;
  background-position: 100% 50%;
  -webkit-mask-image: linear-gradient(to left, transparent 0%, black 12%, black 44%, transparent 60%);
  mask-image: linear-gradient(to left, transparent 0%, black 12%, black 44%, transparent 60%);
}

/* ---------- Settled mark (ARIA-A.svg) ---------- */

.hero-scene__mark {
  position: absolute;
  left: 8%;
  top: 50%;
  width: 96px;
  pointer-events: none;
  opacity: 0;
  transform: translateY(-50%);
}
```

- [ ] **Step 4: Verify the rest state renders correctly with no JS**

```bash
cd docs && python3 -m http.server 8811
```

Open `http://localhost:8811/index.html` in a browser (JS untouched at this point — Task 2 hasn't added `hero-scene.js` yet, so this is a true no-JS check). Confirm:
- Two faint (logo-colored) shapes bleed off the left/right viewport edges behind the title, feathered at both the seam and the outer edge, not hard-cropped.
- No visible seam artifact where the two halves would meet in the center (they should already look like soft fades, not a hard line, at rest).
- The title/subtitle/authors text is fully readable, not overlapped by the logo halves.
- The `ARIA-A.svg` mark is invisible (`opacity: 0`).
- The "What you'll explore" card sits exactly where it did before this change (centered under the lead paragraph, collapsed).

- [ ] **Step 5: Commit**

```bash
git add docs/index.html docs/assets/css/hero-scene.css
git commit -m "feat(website): add hero logo scene markup and rest-state CSS"
```

---

### Task 2: Scroll progress engine

**Files:**
- Create: `docs/assets/js/hero-scene.js`
- Modify: `docs/index.html` (script tag registration)

**Interfaces:**
- Consumes: `#hero-scene` element and `.hero-scene__card` (`<details>`) produced by Task 1.
- Produces: the `--scene-progress` CSS custom property on `#hero-scene`, updated on scroll/resize, `0` at rest and `1` when the 220vh track has fully scrolled past. Also produces the "user manually opened/closed the card" guard consumed by Task 4's auto-open logic.

- [ ] **Step 1: Create `docs/assets/js/hero-scene.js`**

```js
// Drives the hero scroll scene: sets --scene-progress (0..1) on
// #hero-scene as the user scrolls through its 220vh track. All visual
// interpolation lives in hero-scene.css via calc(var(--scene-progress) * ...)
// — this file only ever writes that one custom property, plus toggling
// .hero-scene__card open once past a threshold (never overriding a
// manual user toggle).
(function () {
  'use strict';

  var scene = document.getElementById('hero-scene');
  if (!scene) return;

  var card = scene.querySelector('.hero-scene__card');
  var summary = card ? card.querySelector('summary') : null;
  var cardManuallyToggled = false;

  if (summary) {
    summary.addEventListener('click', function () {
      cardManuallyToggled = true;
    });
  }

  var reduceMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;

  function clamp(value, min, max) {
    return Math.max(min, Math.min(max, value));
  }

  if (reduceMotion) {
    scene.style.setProperty('--scene-progress', 1);
    if (card && !card.open) card.open = true;
    return;
  }

  var ticking = false;

  function updateProgress() {
    ticking = false;
    var rect = scene.getBoundingClientRect();
    var trackable = rect.height - window.innerHeight;
    var progress = trackable > 0 ? clamp(-rect.top / trackable, 0, 1) : 1;
    scene.style.setProperty('--scene-progress', String(progress));

    if (card && !cardManuallyToggled && progress > 0.6 && !card.open) {
      card.open = true;
    }
  }

  function onScrollOrResize() {
    if (!ticking) {
      ticking = true;
      requestAnimationFrame(updateProgress);
    }
  }

  window.addEventListener('scroll', onScrollOrResize, { passive: true });
  window.addEventListener('resize', onScrollOrResize, { passive: true });
  updateProgress();
})();
```

- [ ] **Step 2: Register the script tag**

In `docs/index.html`, in the critical-chrome script block (alongside `theme.js`, `glass-card.js`, etc. — currently around line 790), add after `header-tooltip.js`:

```html
<script src="assets/js/theme.js" defer></script>
<script src="assets/js/glass-card.js" defer></script>
<script src="assets/js/header-tooltip.js" defer></script>
<script src="assets/js/hero-scene.js" defer></script>
<script src="assets/js/reveal.js" defer></script>
```

- [ ] **Step 3: Verify progress updates on scroll**

With the same local server running (`http://localhost:8811/index.html`), open DevTools console and run:

```js
getComputedStyle(document.getElementById('hero-scene')).getPropertyValue('--scene-progress')
```

Scroll down slowly through the hero and re-run the command a few times. Confirm the value moves from `0` toward `1` smoothly (not stuck at `0`, not jumping straight to `1`). Confirm no console errors.

- [ ] **Step 4: Commit**

```bash
git add docs/index.html docs/assets/js/hero-scene.js
git commit -m "feat(website): add scroll progress engine for hero logo scene"
```

---

### Task 3: Progress-driven logo half convergence + settled mark fade-in

**Files:**
- Modify: `docs/assets/css/hero-scene.css`

**Interfaces:**
- Consumes: `--scene-progress` custom property from Task 2, `.hero-scene__logo-half--left/--right` and `.hero-scene__mark` selectors from Task 1.
- Produces: the halves' converge/fade motion and the mark's fade-in/scale motion, consumed visually by Task 5's cross-viewport check (no new class names for later tasks to depend on).

- [ ] **Step 1: Add convergence + fade rules for the logo halves**

In `docs/assets/css/hero-scene.css`, append to `.hero-scene__logo-half--left`:

```css
.hero-scene__logo-half--left {
  left: -8%;
  background-position: 0% 50%;
  -webkit-mask-image: linear-gradient(to right, transparent 0%, black 12%, black 44%, transparent 60%);
  mask-image: linear-gradient(to right, transparent 0%, black 12%, black 44%, transparent 60%);
  transform: translate(calc(var(--scene-progress) * 32vw), -50%);
  opacity: clamp(0, calc(0.16 * (1 - var(--scene-progress) * 1.4)), 0.16);
  filter: blur(0.5px) saturate(90%);
  transition: transform 400ms cubic-bezier(.16, 1, .3, 1), opacity 400ms ease;
  will-change: transform, opacity;
}
```

And to `.hero-scene__logo-half--right` (mirrored translate direction):

```css
.hero-scene__logo-half--right {
  right: -8%;
  background-position: 100% 50%;
  -webkit-mask-image: linear-gradient(to left, transparent 0%, black 12%, black 44%, transparent 60%);
  mask-image: linear-gradient(to left, transparent 0%, black 12%, black 44%, transparent 60%);
  transform: translate(calc(var(--scene-progress) * -32vw), -50%);
  opacity: clamp(0, calc(0.16 * (1 - var(--scene-progress) * 1.4)), 0.16);
  filter: blur(0.5px) saturate(90%);
  transition: transform 400ms cubic-bezier(.16, 1, .3, 1), opacity 400ms ease;
  will-change: transform, opacity;
}
```

(These replace the corresponding rules from Task 1 Step 3 — same selectors, now with the progress-driven `transform`/`opacity`/`filter`/`transition` added.)

- [ ] **Step 2: Add fade-in + scale for the settled mark**

Replace the `.hero-scene__mark` rule from Task 1 Step 3 with:

```css
.hero-scene__mark {
  position: absolute;
  left: 8%;
  top: 50%;
  width: 96px;
  pointer-events: none;
  opacity: var(--scene-progress);
  transform: translateY(-50%) scale(calc(0.7 + var(--scene-progress) * 0.3));
  transition: transform 400ms cubic-bezier(.16, 1, .3, 1), opacity 400ms ease;
  will-change: transform, opacity;
}
```

- [ ] **Step 3: Verify the convergence visually**

With the local server still running, reload and scroll slowly through the hero. Confirm:
- The two halves visibly slide toward the center and fade out together (not one lagging far behind the other).
- The `ARIA-A.svg` mark fades in and grows slightly as the halves fade out, ending fully opaque, small, and positioned at the left.
- Motion feels smooth/eased (matches the `.glass-card` hover easing), not linear or jumpy.
- No layout shift/reflow jank — use DevTools Performance panel or just visually confirm nothing else on the page jumps while scrolling.

- [ ] **Step 4: Commit**

```bash
git add docs/assets/css/hero-scene.css
git commit -m "feat(website): animate logo-half convergence and mark fade-in on scroll"
```

---

### Task 4: Card slide + auto-expand on settle

**Files:**
- Modify: `docs/assets/css/hero-scene.css`

**Interfaces:**
- Consumes: `--scene-progress` from Task 2, `.hero-scene__card` class from Task 1, the auto-open threshold (`progress > 0.6`) already implemented in Task 2's `hero-scene.js`.
- Produces: the card's slide-right visual motion (the open/expand behavior itself is already wired in Task 2's JS; this task only adds the CSS transform + a smoother open transition).

- [ ] **Step 1: Add slide transform to the card**

Append to `docs/assets/css/hero-scene.css`:

```css
/* ---------- Explore card settle position ----------
   The open/close *state* is toggled by hero-scene.js once scroll
   progress passes 0.6 (see updateProgress()); this only adds the
   positional slide so the card visibly moves right as it settles,
   rather than just popping open in place. */

.hero-scene__card {
  transition: transform 400ms cubic-bezier(.16, 1, .3, 1);
  transform: translateX(calc(var(--scene-progress) * 6vw));
}
```

- [ ] **Step 2: Verify the card behavior**

Reload the page at `http://localhost:8811/index.html` and:
1. Scroll slowly through the hero — confirm the card visibly slides right as progress advances and auto-opens (shows its bullet list) once you're past roughly 60% of the way through the scene, without you clicking it.
2. Scroll back up above the hero, then manually click the card's summary to open it by hand, then scroll down through the hero again — confirm the script does not force-close it (the guard in `hero-scene.js` only auto-*opens*, and only if `cardManuallyToggled` is false).
3. Manually click to close the card, scroll back to the top, then scroll down again — confirm it stays closed (manual interaction is respected, no fighting the user).

- [ ] **Step 3: Commit**

```bash
git add docs/assets/css/hero-scene.css
git commit -m "feat(website): slide explore card into settled position on scroll"
```

---

### Task 5: Reduced-motion fallback, title width check, responsive pass

**Files:**
- Modify: `docs/assets/css/hero-scene.css` (reduced-motion/no-motion block)
- Modify: `docs/assets/css/sections.css:96` (only if the manual check in Step 3 finds overlap)

**Interfaces:**
- Consumes: everything from Tasks 1–4.
- Produces: final, ship-ready state — no further tasks depend on this one.

- [ ] **Step 1: Add reduced-motion / no-motion fallback CSS**

Append to `docs/assets/css/hero-scene.css`:

```css
/* ---------- Reduced motion / explicit kill-switch ----------
   Mirrors the body.no-motion convention already used in glass.css.
   Both cases show the fully settled end-state statically, with no
   pinned scroll track (hero-scene.js also short-circuits to
   --scene-progress: 1 for prefers-reduced-motion — see Task 2). */

@media (prefers-reduced-motion: reduce) {
  .hero-scene {
    height: auto;
  }
  .hero-scene__sticky {
    position: static;
    height: auto;
  }
  .hero-scene__logo-half {
    display: none;
  }
}

body.no-motion .hero-scene {
  height: auto;
}
body.no-motion .hero-scene__sticky {
  position: static;
  height: auto;
}
body.no-motion .hero-scene__logo-half {
  display: none;
}
```

- [ ] **Step 2: Verify reduced-motion behavior**

In Chrome DevTools, open the Rendering tab (Cmd+Shift+P → "Show Rendering"), set "Emulate CSS media feature prefers-reduced-motion" to "reduce", then reload `http://localhost:8811/index.html`. Confirm:
- No pinned/tall scroll track — the hero is normal height.
- The `ARIA-A.svg` mark is visible immediately (opacity 1) at its settled position; the two logo halves are not shown (`display: none`).
- The "What you'll explore" card is already open.
- Turn the emulation back off before continuing.

- [ ] **Step 3: Check for text/logo overlap at common viewports and narrow title width if needed**

With the local server running, use DevTools device toolbar to check 390px (mobile), 768px (tablet), and 1440px (desktop) widths. At each, scroll through the hero and watch the feathered edge of each logo half relative to the title/subtitle text.

If the feathered edge visibly brushes against the text at any of these widths, narrow the hero content column in `docs/assets/css/sections.css` — find this rule (around line 96):

```css
.tile--hero .tile__content {
  max-width: 880px;                              /* Wider hero text to fit title in 4 lines */
```

and change `880px` to `760px`:

```css
.tile--hero .tile__content {
  max-width: 760px;                              /* Narrowed to keep clear of the hero-scene logo halves at the sides */
```

Re-check all three widths after the change. If there is no overlap at any width, skip this edit entirely (don't narrow the column speculatively).

- [ ] **Step 4: Full manual regression pass**

At each of the three widths above, with motion enabled (no emulation): scroll from the very top of the page down through `#problem`. Confirm:
- The floating pill header's own scroll/reveal behavior (unrelated `reveal.js` fades on later sections) still fires normally — no collision with the new scroll listener.
- No console errors at any point.
- The hero scene fully releases (pin stops) once `--scene-progress` reaches 1, and `#problem` scrolls in normally beneath it, per the design's confirmed "release into normal flow" end-behavior.

- [ ] **Step 5: Commit**

```bash
git add docs/assets/css/hero-scene.css docs/assets/css/sections.css
git commit -m "fix(website): reduced-motion fallback and responsive pass for hero logo scene"
```

---

### Task 6: Redesign convergence + fix critical bugs from final review

After Tasks 1-5 landed, two things happened: (1) the user watched the actual
rendered page and corrected the design intent, and (2) the final
whole-branch review (Opus) independently found three critical bugs that
happened to explain exactly what the user saw ("it just disappears").

**User's corrected design intent (confirmed):**
- The two logo halves start pinned near the true left/right viewport edges
  (not ~46vw boxes at -8%), with a gap clearly wider than the text column.
- Scrolling does not fade the halves to invisible — they translate toward
  each other while *simultaneously* sharpening (blur → 0) and becoming more
  opaque (faint → solid), staying visible throughout. Clearer the more you
  scroll.
- At full convergence (progress 1), there is no separate "settled mark"
  using `ARIA-A.svg` — the two halves simply form the complete
  `ARIA-logo.svg` image.
- That merge point is itself left-of-center (not dead-center), so this is
  a *single continuous* scroll interpolation — not a two-phase "merge to
  center, then slide left" animation. The asymmetric rest/target math
  achieves the left-leaning merge directly (see the `--logo-merge-x` CSS
  custom property in `hero-scene.css`).

**Critical bugs found by final review, fixed as part of this same task:**
1. `docs/index.html` referenced `assets/figures/ARIA-A.svg`, which was
   never copied into `docs/assets/figures/` — 404, mark never rendered.
   Resolved by removing the separate mark element entirely (superseded by
   the user's corrected design above, which doesn't need it).
2. `hero-scene.js` set `card.open = true` directly to auto-expand the
   "What you'll explore" card. `detail-toggle.js` only reveals the panel
   body in response to a real click on `<summary>` (`.is-open` class +
   explicit max-height) — setting `.open` directly desyncs the two,
   leaving the body visually collapsed and the user's next manual click
   toggling backwards. This exact anti-pattern is already documented and
   avoided in `tour.js`'s `openDetails()`. Fixed by firing a real
   `summary.click()`, guarded by an `isProgrammaticOpen` flag so the
   click listener doesn't mistake it for manual interaction.
3. The card carries `.glass-card`, which has an idle-float `animation`
   (`glass-float-slow` via `.glass-card--compact`) in `glass.css`. CSS
   animations always win the cascade over a plain `transform`
   declaration, so `.hero-scene__card`'s slide transform never took
   effect. Fixed by adding the existing `.glass-card--no-float` utility
   class (already defined in `glass.css` for exactly this situation) to
   the card's class list in `docs/index.html`.
4. `.hero-scene__sticky` was `height: 100vh; overflow: hidden`, which
   clips hero content on viewports shorter than the hero's natural
   height (~830–970px). Fixed with `min-height: 100vh; height: auto;
   overflow-x: hidden; overflow-y: visible;` — sticky pinning still
   works, horizontal bleed is still contained, but tall content is no
   longer clipped.
5. The hero title column (`max-width: 880px`) likely overlapped the
   logo halves' feathered tail at common desktop widths (~1024–1280px).
   Narrowed to `640px` in `docs/assets/css/sections.css`.

**Known limitation:** neither the implementer(s) nor the controller have
working browser tooling in this environment (Chrome extension not
connected) — this task's CSS math (asymmetric translateX targets, opacity/
blur interpolation) was authored and self-checked arithmetically, but not
visually verified. The exact `--logo-merge-x`, `--logo-rest-inset`,
`--logo-half-width`, `--logo-rest-opacity`, and `--logo-rest-blur` values
in `hero-scene.css` are exposed as tunable custom properties specifically
so they can be retuned after a real look in a browser, without needing to
re-derive the interpolation formulas.

- [x] Rewrite `docs/assets/css/hero-scene.css`: continuous asymmetric
      convergence, no separate mark, sticky height/overflow fix.
- [x] Rewrite `docs/assets/js/hero-scene.js`: `summary.click()` instead
      of `.open` assignment, guarded against self-triggering the manual-
      toggle flag.
- [x] `docs/index.html`: remove the `ARIA-A.svg` mark `<img>`, add
      `glass-card--no-float` to the card's class list.
- [x] `docs/assets/css/sections.css`: narrow `.tile--hero .tile__content`
      max-width 880px → 640px.
- [ ] Commit and get a task review pass on this diff.
- [ ] Manual browser verification by the user (or a future session with
      working browser tooling) — specifically: gap width and merge point
      at common viewports, blur/opacity curve feel, card/logo pairing per
      spec's reference layout, and the 640px title width's actual fit.
