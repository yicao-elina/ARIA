# Guided Site Tour v2 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the existing modal-style "Take a Tour" with a guided walkthrough that shows the whole section first, then reveals elements one-by-one via an SVG mask with springy bloom, and plays a ~1s/element "Do it for me" timeline that fires each element's action.

**Architecture:** Single IIFE in `docs/assets/js/tour.js` rewritten into three renderers (canvas frame, mask, callout/panel) + one orchestrator class. The existing `STOPS` data model is preserved and extended with an optional `action` field per focus point. No other files touched, no new dependencies.

**Tech Stack:** Vanilla JS (ES2017+), SVG masks, CSS keyframes, no build step. Targets the existing site (Apple-style aesthetic, `prefers-reduced-motion` aware).

## Global Constraints

- One file: `docs/assets/js/tour.js`. Do not edit `index.html` or any CSS file.
- No new dependencies. No build step. ES2017+ syntax only.
- All exported surface (DOM IDs, CSS class names) is internal — the IIFE exposes nothing.
- Honor `prefers-reduced-motion: reduce` for every animation.
- Preserve existing public hooks consumed by other code (none today — `STOPS` is local).
- Commit messages follow the repo's existing style: `<type>(scope): <description>` (per `common/git-workflow.md`).
- Attribution: do NOT add `Co-Authored-By:` lines (disabled globally).

---

### Task 1: Add `action` field to `STOPS` data

**Files:**
- Modify: `docs/assets/js/tour.js:16-143` (`STOPS` array)

**Interfaces:**
- Consumes: the existing `STOPS` array
- Produces: same `STOPS` array, with an added optional `action: { kind: "click" | "open-details" }` field on each `focusPoints[]` entry and `actionPoint` where appropriate.

Add `action` to these entries (and only these) so the "Do it for me" timeline has something to fire:

```js
// In the "problem" stop, focusPoints[0]:
{ selector: "#problem .tunneling-panel--naive-kg .tunneling-segment--error",
  label: "This is contextual tunneling: a plausible-sounding claim built by over-anchoring on partial KG evidence." },
// (no action — purely explanatory)

// In the "problem" stop, focusPoints[1]:
{ selector: "#problem .tunneling-panel--baseline",
  label: "The baseline LLM, using only parametric knowledge, avoids this trap — but has no causal grounding at all." },
// (no action)

// In the "problem" stop, actionPoint:
actionPoint: {
  selector: "#problem .tunneling-example-btn:nth-of-type(2)",
  label: "Try Example 2 to see the same failure mode show up on a different query.",
  action: { kind: "click" }
},

// In the "cascade" stop, focusPoints[0]:
{ selector: "#cascade .tr-example-btns .tr-example-btn",
  label: "Each pill is a worked example — click one to route it through a different tier.",
  action: { kind: "click" } },

// In the "cascade" stop, actionPoint:
actionPoint: {
  selector: "#cascade .tr-run-btn",
  label: "Click “Route Query” to send this example through the three-tier cascade.",
  action: { kind: "click" }
},

// In the "kg-section" stop, focusPoints[0]:
{ selector: "#kg-section svg.kg-svg",
  label: "Nodes are PSP entities — hover any node to trace its causal connections." },
// (no action)

// In the "kg-section" stop, actionPoint:
actionPoint: {
  selector: "#kg-section .kg-filter-material",
  label: "Try switching materials — the graph re-filters to just that system's PSP edges.",
  action: { kind: "change" }    // see Task 5 for the "change" kind
},

// In the "tier-deep-dive" stop, focusPoints[0]:
{ selector: "#tier-deep-dive .tier-1-detail summary",
  label: "This one's already open — see the full causal trace from processing to property below.",
  action: { kind: "open-details" } },

// In the "tier-deep-dive" stop, focusPoints[1]:
{ selector: "#tier-deep-dive .tier-3-detail summary",
  label: "This example honestly flags low confidence instead of guessing with false certainty.",
  action: { kind: "open-details" } },

// In the "tier-deep-dive" stop, actionPoint:
actionPoint: {
  selector: "#tier-deep-dive .tier-2-detail summary",
  label: "Expand this one to see ARIA validate physical constraints before transferring MoS₂'s mechanism to MoSe₂.",
  action: { kind: "open-details" }
},

// In the "results" stop, focusPoints[0]:
{ selector: "#results .mt-td--best",
  label: "Cells highlighted like this mark the best score in that column." },
// (no action)

// In the "results" stop, actionPoint:
actionPoint: {
  selector: '#results-toggles button[data-metric="inverse"]',
  label: "Switch to Inverse Design — this is where the tier asymmetry really shows.",
  action: { kind: "click" }
},

// In the "robustness" stop, actionPoint:
actionPoint: {
  selector: "#robustness-slider",
  label: "Drag this to delete graph edges and watch ARIA adapt versus a naive KG baseline.",
  action: { kind: "click" }    // a simple click on the slider host focuses it; the real interaction is dragging, which is manual
},

// In the "trace-audit" stop, focusPoints[0]:
{ selector: '.trace-step[data-step="3"] .completeness-bar',
  label: "The causal-completeness check that gates whether evidence is trustworthy enough to answer from." },
// (no action)

// In the "trace-audit" stop, actionPoint:
actionPoint: {
  selector: '.trace-step[data-step="4"] details.detail-toggle summary',
  label: "Expand to see the cited evidence behind this step.",
  action: { kind: "open-details" }
}
```

- [ ] **Step 1: Edit `STOPS` to add the `action` fields above**
- [ ] **Step 2: Commit**

```bash
git add docs/assets/js/tour.js
git commit -m "feat(tour): add action field to STOPS for Do-it-for-me timeline"
```

---

### Task 2: Add CONSTANTS, utilities, and reducedMotion helper

**Files:**
- Modify: `docs/assets/js/tour.js` (insert new section after `STOPS`, before the existing `class SiteTour {`)

**Interfaces:**
- Consumes: `STOPS` (data layer)
- Produces:
  - `CONSTANTS` object exported into the IIFE scope (used by renderers and orchestrator)
  - `utils` object: `{ getEl(sel), dispatchClick(el), openDetails(summaryEl), reducedMotion() }`

**Why this comes first:** Renderers and the orchestrator both depend on these.

Insert the following block immediately after the closing `];` of `STOPS` and before `const HIGHLIGHT_CLASS = ...`:

```js
  // ── Constants ──
  // Tunable from one place so the "feel" can be adjusted without hunting.
  const CONSTANTS = {
    // Per-element play cadence (ms). Total ≈1000ms with an action, ≈720ms without.
    PLAY_SPRING_IN_MS: 360,
    PLAY_PRE_ACTION_MS: 100,
    PLAY_POST_ACTION_MS: 360,
    PLAY_NEXT_GAP_MS: 180,
    // Manual reveal animation
    REVEAL_SPRING_MS: 420,
    MASK_HOLE_BLOOM_MS: 280,
    CALLOUT_SPRING_MS: 320,
    // Sub-step scroll behavior
    SCROLL_SETTLE_MS: 550,
    // Pulse on revealed elements
    BREATH_PERIOD_MS: 2400,
    // Z-indices (scrim < mask < callout < panel)
    Z_SCRIM: 400,
    Z_HIGHLIGHT: 500,
    Z_FOCUS: 450,
    Z_ACTION: 480,
    Z_MASK: 460,
    Z_CALLOUT: 470,
    Z_CONNECTOR: 460,
    Z_PANEL: 2000,
    // Spring easing — slightly bouncier than today's tour
    SPRING: "cubic-bezier(0.34, 1.56, 0.64, 1)",
    // Smooth (non-bouncy) for scrim fades
    SMOOTH: "cubic-bezier(0.22, 0.61, 0.36, 1)",
  };

  // ── Utilities ──
  const utils = {
    getEl(selector) {
      try {
        return document.querySelector(selector);
      } catch (e) {
        return null;
      }
    },
    reducedMotion() {
      return (
        window.matchMedia &&
        window.matchMedia("(prefers-reduced-motion: reduce)").matches
      );
    },
    // Fire a real click that listeners attached with addEventListener
    // will receive. We dispatch MouseEvent in addition to calling .click()
    // so delegated handlers (event.target.closest(...)) also fire.
    dispatchClick(el) {
      if (!el) return;
      if (typeof el.click === "function") el.click();
      el.dispatchEvent(
        new MouseEvent("click", { bubbles: true, cancelable: true, view: window })
      );
    },
    openDetails(summaryEl) {
      if (!summaryEl) return;
      const details = summaryEl.closest("details");
      if (!details) return;
      if (!details.open) {
        details.open = true;
        // Some pages (this one) listen for the 'toggle' event to re-render.
        details.dispatchEvent(new Event("toggle"));
      }
    },
    // Fire a "change" on a <select> so onchange handlers run.
    dispatchChange(el) {
      if (!el) return;
      el.dispatchEvent(
        new Event("change", { bubbles: true, cancelable: true })
      );
    },
  };
```

- [ ] **Step 1: Insert the `CONSTANTS` and `utils` block as shown**
- [ ] **Step 2: Commit**

```bash
git add docs/assets/js/tour.js
git commit -m "feat(tour): add CONSTANTS and shared utilities"
```

---

### Task 3: Implement the canvas-frame renderer

**Files:**
- Modify: `docs/assets/js/tour.js` (insert after the `utils` block)

**Interfaces:**
- Consumes: `sectionEl` (HTMLElement), `{ stepNumber, totalSteps, sectionTitle, onEnd }`
- Produces: a `tourCanvas` object `{ root, setSubStep(done, total), destroy() }`

The canvas is the rounded "Tour mode" overlay that hugs the section. It does NOT mask the section — that comes later via the mask renderer. The canvas only shows:
- A rounded outline hugging the section's bounding rect
- A corner pill: `Tour mode · Step 3/9 · PSP Hierarchy`
- A thin sub-step progress strip below the pill
- A small "End Tour ✕" ghost button in the top-right

Insert the following renderer:

```js
  // ── Renderer: canvas frame ──
  // A rounded outline + chrome that hugs a section. Sits ABOVE the
  // section's content (so the section is fully visible inside) but
  // BELOW the mask (z-indices in CONSTANTS). The first frame of each
  // section shows ONLY the canvas, with no mask.
  function createCanvasFrame(sectionEl, meta) {
    const root = document.createElement("div");
    root.className = "tour-canvas";
    root.setAttribute("aria-hidden", "true");
    sectionEl.style.position = sectionEl.style.position || "relative";
    sectionEl.appendChild(root);

    const pill = document.createElement("div");
    pill.className = "tour-canvas__pill";
    root.appendChild(pill);

    const strip = document.createElement("div");
    strip.className = "tour-canvas__strip";
    root.appendChild(strip);

    const endBtn = document.createElement("button");
    endBtn.type = "button";
    endBtn.className = "tour-canvas__end";
    endBtn.setAttribute("aria-label", "End tour");
    endBtn.textContent = "End Tour ✕";
    endBtn.addEventListener("click", () => meta.onEnd && meta.onEnd());
    root.appendChild(endBtn);

    function render() {
      const rect = sectionEl.getBoundingClientRect();
      // Position the canvas as a fixed overlay matching the section's
      // viewport position. We use `position: fixed` because the section
      // can scroll under the viewport while the tour is mid-step.
      root.style.left = rect.left + "px";
      root.style.top = rect.top + "px";
      root.style.width = rect.width + "px";
      root.style.height = rect.height + "px";
      pill.textContent =
        "Tour mode · Step " + meta.stepNumber + " of " + meta.totalSteps +
        " · " + meta.sectionTitle;
    }

    function setSubStep(done, total) {
      strip.innerHTML = "";
      for (let i = 0; i < total; i++) {
        const seg = document.createElement("span");
        seg.className =
          "tour-canvas__seg" + (i < done ? " is-done" : "");
        strip.appendChild(seg);
      }
    }

    function destroy() {
      root.remove();
    }

    render();
    return { root, render, setSubStep, destroy };
  }
```

- [ ] **Step 1: Insert the `createCanvasFrame` function as shown**
- [ ] **Step 2: Commit**

```bash
git add docs/assets/js/tour.js
git commit -m "feat(tour): add canvas-frame renderer"
```

---

### Task 4: Implement the SVG mask renderer

**Files:**
- Modify: `docs/assets/js/tour.js` (insert after `createCanvasFrame`)

**Interfaces:**
- Consumes: `sectionEl` (HTMLElement)
- Produces: a `tourMask` object `{ root, setRevealed(els), destroy() }`

The mask is a single `<svg>` overlay clipped to the section. It draws a dark glass layer and "punches" rounded-rect holes through it for each revealed element using an SVG `<mask>`. Reveals are accumulating — holes only ever grow.

```js
  // ── Renderer: mask ──
  // A single SVG that covers the section, draws a dark glass layer,
  // and punches rounded-rect holes through it for every revealed
  // element. Holes only ever grow (reveals are accumulating).
  function createMask(sectionEl) {
    const root = document.createElementNS("http://www.w3.org/2000/svg", "svg");
    root.setAttribute("class", "tour-mask-svg");
    root.setAttribute("aria-hidden", "true");
    sectionEl.appendChild(root);

    // Defs: a single mask whose white shapes become "holes".
    const defs = document.createElementNS("http://www.w3.org/2000/svg", "defs");
    const mask = document.createElementNS("http://www.w3.org/2000/svg", "mask");
    mask.setAttribute("id", "tour-mask-cutout");
    // The mask starts fully BLACK (= nothing visible through the mask).
    const bg = document.createElementNS("http://www.w3.org/2000/svg", "rect");
    bg.setAttribute("x", "0");
    bg.setAttribute("y", "0");
    bg.setAttribute("width", "100%");
    bg.setAttribute("height", "100%");
    bg.setAttribute("fill", "black");
    mask.appendChild(bg);
    defs.appendChild(mask);
    root.appendChild(defs);

    // The visible dark layer references the mask.
    const layer = document.createElementNS("http://www.w3.org/2000/svg", "rect");
    layer.setAttribute("x", "0");
    layer.setAttribute("y", "0");
    layer.setAttribute("width", "100%");
    layer.setAttribute("height", "100%");
    layer.setAttribute("fill", "rgba(6, 10, 22, 0.45)");
    layer.setAttribute("mask", "url(#tour-mask-cutout)");
    root.appendChild(layer);

    // Cache of currently-rendered hole rects, keyed by element identity.
    // We re-measure on every setRevealed() call.
    const holeRects = new WeakMap();

    function render() {
      const sRect = sectionEl.getBoundingClientRect();
      root.setAttribute("viewBox", `0 0 ${sRect.width} ${sRect.height}`);
      root.setAttribute("width", sRect.width);
      root.setAttribute("height", sRect.height);
      root.style.left = "0px";
      root.style.top = "0px";
      root.style.width = sRect.width + "px";
      root.style.height = sRect.height + "px";
    }

    function setRevealed(els) {
      render();
      // Remove all currently-rendered hole rects; re-add fresh ones
      // so re-measured positions are accurate.
      mask.querySelectorAll("rect.hole").forEach((n) => n.remove());
      els.forEach((el, i) => {
        const r = el.getBoundingClientRect();
        const sRect = sectionEl.getBoundingClientRect();
        // Position relative to the section's top-left.
        const x = r.left - sRect.left - 6;
        const y = r.top - sRect.top - 6;
        const w = r.width + 12;
        const h = r.height + 12;
        const hole = document.createElementNS("http://www.w3.org/2000/svg", "rect");
        hole.setAttribute("class", "hole");
        hole.setAttribute("x", x);
        hole.setAttribute("y", y);
        hole.setAttribute("width", w);
        hole.setAttribute("height", h);
        // Animate rx/ry from 4 → 12 for the "bloom" effect on the newest hole.
        const isNewest = i === els.length - 1;
        const reduced = utils.reducedMotion();
        hole.setAttribute("rx", isNewest && !reduced ? 4 : 12);
        hole.setAttribute("ry", isNewest && !reduced ? 4 : 12);
        hole.setAttribute("fill", "white");
        if (isNewest && !reduced) {
          // CSS handles the rx/ry transition via the .hole class.
          hole.classList.add("hole--blooming");
        }
        mask.appendChild(hole);
        holeRects.set(el, hole);
      });
    }

    function destroy() {
      root.remove();
    }

    render();
    return { root, render, setRevealed, destroy };
  }
```

- [ ] **Step 1: Insert the `createMask` function as shown**
- [ ] **Step 2: Commit**

```bash
git add docs/assets/js/tour.js
git commit -m "feat(tour): add SVG mask renderer with accumulating cutouts"
```

---

### Task 5: Implement the callout renderer

**Files:**
- Modify: `docs/assets/js/tour.js` (insert after `createMask`)

**Interfaces:**
- Consumes: `targetEl` (HTMLElement), `{ text, onDismiss }`
- Produces: a `tourCallout` object `{ root, reposition(), destroy() }`

The callout is a small glass bubble that flows in next to its target. It does NOT have an SVG connector line — it just sits to the left or right of the target, whichever has more free space.

```js
  // ── Renderer: callout ──
  // Small glass bubble that flows in next to its target. No SVG line —
  // the proximity is enough since the target is lit and the section
  // is dimmed.
  function createCallout(targetEl, opts) {
    const root = document.createElement("div");
    root.className = "tour-callout glass-card";
    const p = document.createElement("p");
    p.className = "tour-callout__text";
    p.textContent = opts.text;
    root.appendChild(p);
    document.body.appendChild(root);

    function place() {
      const tRect = targetEl.getBoundingClientRect();
      const margin = 16;
      const gap = 18;
      // Measure after content is in the DOM.
      const cRect = root.getBoundingClientRect();
      const goesLeft = tRect.left + tRect.width / 2 > window.innerWidth / 2;
      let left = goesLeft
        ? tRect.left - gap - cRect.width
        : tRect.right + gap;
      left = Math.min(
        Math.max(left, margin),
        window.innerWidth - cRect.width - margin
      );
      let top = tRect.top + tRect.height / 2 - cRect.height / 2;
      top = Math.min(
        Math.max(top, margin),
        window.innerHeight - cRect.height - margin
      );
      root.style.left = left + "px";
      root.style.top = top + "px";
      root.dataset.side = goesLeft ? "left" : "right";
    }

    function reposition() {
      place();
    }

    function destroy() {
      root.remove();
    }

    place();
    return { root, reposition, destroy };
  }
```

- [ ] **Step 1: Insert the `createCallout` function as shown**
- [ ] **Step 2: Commit**

```bash
git add docs/assets/js/tour.js
git commit -m "feat(tour): add callout renderer"
```

---

### Task 6: Implement the panel renderer

**Files:**
- Modify: `docs/assets/js/tour.js` (insert after `createCallout`)

**Interfaces:**
- Consumes: a state object `{ stepNumber, totalSteps, sectionTitle, subStepDone, subStepTotal, canBack, canDoIt, canNext, isPlaying, isPaused, onBack, onDoIt, onPause, onResume, onNext, onEnd }`
- Produces: a `tourPanel` object `{ root, setState(state), destroy() }`

The panel renders the bottom-right control panel. The primary button slot morphs based on state (see spec §5). All buttons except `End Tour` and `Back` are always rendered — only their labels/visibility change.

```js
  // ── Renderer: panel ──
  // Bottom-right control panel. The primary slot morphs based on state.
  function createPanel(initial) {
    const root = document.createElement("div");
    root.className = "tour-panel glass-card";
    root.setAttribute("role", "dialog");
    root.setAttribute("aria-label", "Guided tour");
    document.body.appendChild(root);

    const progress = document.createElement("div");
    progress.className = "tour-panel__progress";
    root.appendChild(progress);

    const title = document.createElement("div");
    title.className = "tour-panel__title";
    root.appendChild(title);

    const dots = document.createElement("div");
    dots.className = "tour-panel__dots";
    root.appendChild(dots);

    const controls = document.createElement("div");
    controls.className = "tour-panel__controls";
    root.appendChild(controls);

    // Buttons are recreated on every state change to keep listeners fresh.
    function render(state) {
      progress.textContent =
        "Step " + state.stepNumber + " of " + state.totalSteps;
      title.textContent = state.sectionTitle;
      dots.innerHTML = "";
      for (let i = 0; i < state.subStepTotal; i++) {
        const d = document.createElement("span");
        d.className =
          "tour-panel__dot" + (i < state.subStepDone ? " is-done" : "");
        dots.appendChild(d);
      }
      controls.innerHTML = "";
      if (state.canBack) {
        const back = document.createElement("button");
        back.type = "button";
        back.className = "tour-btn tour-btn--ghost";
        back.textContent = "◀ Back";
        back.addEventListener("click", () => state.onBack && state.onBack());
        controls.appendChild(back);
      }
      const spacer = document.createElement("div");
      spacer.className = "tour-panel__spacer";
      controls.appendChild(spacer);

      // Primary slot
      const primary = document.createElement("button");
      primary.type = "button";
      primary.className = "tour-btn tour-btn--primary";
      if (state.isPlaying) {
        primary.textContent = "⏸ Pause";
        primary.addEventListener("click", () => state.onPause && state.onPause());
      } else if (state.isPaused) {
        primary.textContent = "▶ Resume";
        primary.addEventListener("click", () => state.onResume && state.onResume());
      } else if (state.subStepDone >= state.subStepTotal) {
        primary.textContent = "Next ▸";
        primary.addEventListener("click", () => state.onNext && state.onNext());
      } else {
        primary.textContent = "Next ▸";
        primary.addEventListener("click", () => state.onNext && state.onNext());
      }
      controls.appendChild(primary);

      // "Do it for me" — secondary, only when not already primary and there
      // are focus/action points to play.
      if (
        !state.isPlaying &&
        !state.isPaused &&
        state.canDoIt &&
        state.subStepDone < state.subStepTotal
      ) {
        const doIt = document.createElement("button");
        doIt.type = "button";
        doIt.className = "tour-btn tour-btn--ghost tour-btn--doit";
        doIt.textContent = "Do it for me ▶";
        doIt.addEventListener("click", () => state.onDoIt && state.onDoIt());
        controls.appendChild(doIt);
      }

      const end = document.createElement("button");
      end.type = "button";
      end.className = "tour-btn tour-btn--ghost";
      end.textContent = "End";
      end.addEventListener("click", () => state.onEnd && state.onEnd());
      controls.appendChild(end);
    }

    function setState(state) {
      render(state);
    }

    render(initial);
    return { root, setState, destroy: () => root.remove() };
  }
```

- [ ] **Step 1: Insert the `createPanel` function as shown**
- [ ] **Step 2: Commit**

```bash
git add docs/assets/js/tour.js
git commit -m "feat(tour): add panel renderer with morphing primary slot"
```

---

### Task 7: Implement the `SiteTour` orchestrator (state + lifecycle)

**Files:**
- Modify: `docs/assets/js/tour.js` (replace the existing `class SiteTour { ... }` with a new orchestrator)

**Interfaces:**
- Consumes: `STOPS`, `CONSTANTS`, `utils`, the four renderers
- Produces: a `SiteTour` class with methods `{ start, end, next, back, play, pause, resume, isPlaying }`

This is the largest task. The orchestrator owns:
- `_index` (current stop), `_subIndex` (current sub-step within the stop)
- `_revealed` (array of revealed elements for the current section)
- `_mode` ('idle' | 'playing' | 'paused')
- `_playCancel` (a function that aborts the current play loop)
- `_isAdvancing` (spam guard)

It coordinates: canvas frame, mask, callout, panel, `onEnter`/`onLeave`, scroll, keyboard.

```js
  // ── Orchestrator: SiteTour ──
  class SiteTour {
    constructor(stops) {
      this.stops = stops.filter((stop) => document.getElementById(stop.id));
      this._index = -1;
      this._subIndex = -1;        // -1 = first-frame canvas (nothing revealed yet)
      this._revealed = [];        // elements revealed in the current section
      this._mode = "idle";        // 'idle' | 'playing' | 'paused'
      this._playCancel = null;
      this._isAdvancing = false;
      this._active = false;
      this._canvas = null;
      this._mask = null;
      this._callout = null;
      this._panel = null;
      this._onKeydown = this._onKeydown.bind(this);
      this._onViewportChange = this._reposition.bind(this);
      this._rafScheduled = false;
      this._injectStyles();
    }

    start() {
      if (!this.stops.length || this._active) return;
      this._active = true;
      this._index = 0;
      this._subIndex = -1;
      this._revealed = [];
      this._mode = "idle";
      document.addEventListener("keydown", this._onKeydown);
      window.addEventListener("scroll", this._onViewportChange, { passive: true });
      window.addEventListener("resize", this._onViewportChange);
      this._goto(0, -1);
    }

    end() {
      if (!this._active) return;
      this._cancelPlay();
      const cur = this.stops[this._index];
      if (cur && typeof cur.onLeave === "function") {
        try { cur.onLeave(document.getElementById(cur.id)); } catch (e) {}
      }
      this._destroyRenderers();
      document.removeEventListener("keydown", this._onKeydown);
      window.removeEventListener("scroll", this._onViewportChange);
      window.removeEventListener("resize", this._onViewportChange);
      this._active = false;
    }

    next() {
      if (this._isAdvancing || !this._active) return;
      this._isAdvancing = true;
      try {
        const cur = this.stops[this._index];
        const totalSubSteps = this._subStepTotal(cur);
        if (this._subIndex < totalSubSteps - 1) {
          this._goto(this._index, this._subIndex + 1);
        } else {
          // Last sub-step done — advance to next section.
          if (this._index >= this.stops.length - 1) {
            this.end();
          } else {
            this._goto(this._index + 1, -1);
          }
        }
      } finally {
        this._isAdvancing = false;
      }
    }

    back() {
      if (this._isAdvancing || !this._active) return;
      this._isAdvancing = true;
      try {
        if (this._subIndex > -1) {
          this._goto(this._index, this._subIndex - 1);
        } else if (this._index > 0) {
          this._goto(this._index - 1, this._subStepTotal(this.stops[this._index - 1]) - 1);
        }
      } finally {
        this._isAdvancing = false;
      }
    }

    play() {
      if (this._mode === "playing" || !this._active) return;
      const cur = this.stops[this._index];
      const total = this._subStepTotal(cur);
      // If everything's already revealed, restart the section.
      if (this._subIndex >= total - 1) {
        this._cancelPlay();
        this._goto(this._index, -1);
      }
      this._mode = "playing";
      this._refreshPanel();
      let i = this._subIndex + 1;
      let cancelled = false;
      this._playCancel = () => { cancelled = true; };

      const step = () => {
        if (cancelled || !this._active) return;
        if (i >= total) {
          this._mode = "idle";
          this._playCancel = null;
          this._refreshPanel();
          return;
        }
        this._goto(this._index, i);
        const el = this._currentSubStepEl();
        const pt = this._currentSubStepPoint();
        const fire = () => {
          if (pt && pt.action) {
            if (pt.action.kind === "click") utils.dispatchClick(el);
            else if (pt.action.kind === "open-details") utils.openDetails(el);
            else if (pt.action.kind === "change") utils.dispatchChange(el);
          }
        };
        const next = () => {
          if (cancelled || !this._active) return;
          if (this._mode === "paused") {
            // Pause: schedule a resume check (poll lightly).
            const wait = setInterval(() => {
              if (cancelled || !this._active) { clearInterval(wait); return; }
              if (this._mode === "playing") {
                clearInterval(wait);
                i += 1;
                window.setTimeout(step, 60);
              }
            }, 120);
            return;
          }
          i += 1;
          window.setTimeout(step, CONSTANTS.PLAY_NEXT_GAP_MS);
        };
        window.setTimeout(fire, CONSTANTS.PLAY_SPRING_IN_MS + CONSTANTS.PLAY_PRE_ACTION_MS);
        window.setTimeout(next, CONSTANTS.PLAY_SPRING_IN_MS + CONSTANTS.PLAY_PRE_ACTION_MS + CONSTANTS.PLAY_POST_ACTION_MS);
      };
      window.setTimeout(step, 60);
    }

    pause() {
      if (this._mode !== "playing") return;
      this._mode = "paused";
      this._refreshPanel();
    }

    resume() {
      if (this._mode !== "paused") return;
      this._mode = "playing";
      this._refreshPanel();
    }

    isPlaying() { return this._mode === "playing"; }

    // ── Internals ──

    _subStepTotal(stop) {
      // Includes both focusPoints (excluding null labels) and the actionPoint.
      const fps = (stop && stop.focusPoints) ? stop.focusPoints.length : 0;
      return fps + (stop && stop.actionPoint ? 1 : 0);
    }

    _subStepPoint(stop, subIndex) {
      const fps = (stop.focusPoints || []);
      if (subIndex < fps.length) return fps[subIndex];
      if (stop.actionPoint) return stop.actionPoint;
      return null;
    }

    _currentSubStepPoint() {
      return this._subStepPoint(this.stops[this._index], this._subIndex);
    }

    _currentSubStepEl() {
      const pt = this._currentSubStepPoint();
      if (!pt) return null;
      return utils.getEl(pt.selector);
    }

    _cancelPlay() {
      if (this._playCancel) {
        this._playCancel();
        this._playCancel = null;
      }
      this._mode = "idle";
    }

    _destroyRenderers() {
      if (this._canvas) { this._canvas.destroy(); this._canvas = null; }
      if (this._mask)   { this._mask.destroy();   this._mask = null; }
      if (this._callout){ this._callout.destroy();this._callout = null; }
      if (this._panel)  { this._panel.destroy();  this._panel = null; }
    }

    _goto(index, subIndex) {
      // Clean up the previous stop's onLeave.
      const prev = this.stops[this._index];
      if (prev && prev !== this.stops[index]) {
        if (typeof prev.onLeave === "function") {
          try { prev.onLeave(document.getElementById(prev.id)); } catch (e) {}
        }
        this._destroyRenderers();
        this._revealed = [];
      } else if (prev === this.stops[index] && subIndex < this._subIndex) {
        // Going back within a section — re-reveal only the up-to-subIndex elements.
        this._revealed = this._revealed.slice(0, subIndex + 1);
        if (this._callout) { this._callout.destroy(); this._callout = null; }
      } else if (prev === this.stops[index] && subIndex > this._subIndex) {
        // Going forward within a section — append the new element.
        const el = utils.getEl(this._subStepPoint(this.stops[index], subIndex).selector);
        if (el) this._revealed.push(el);
      }

      this._index = index;
      this._subIndex = subIndex;
      const stop = this.stops[index];
      const sectionEl = document.getElementById(stop.id);
      if (!sectionEl) { this.next(); return; }

      // Fire onEnter for the new stop (only when we just changed stop).
      if (prev !== stop) {
        if (typeof stop.onEnter === "function") {
          try { stop.onEnter(sectionEl); } catch (e) {}
        }
      }

      // Scroll into view (smooth, unless reduced motion).
      const reduced = utils.reducedMotion();
      sectionEl.scrollIntoView({
        behavior: reduced ? "auto" : "smooth",
        block: "center",
      });

      // Build / update renderers.
      this._ensureRenderers(sectionEl, stop);
      this._applyRevealState(sectionEl, stop, subIndex);
      this._refreshPanel();
    }

    _ensureRenderers(sectionEl, stop) {
      if (!this._canvas) {
        this._canvas = createCanvasFrame(sectionEl, {
          stepNumber: this._index + 1,
          totalSteps: this.stops.length,
          sectionTitle: stop.title,
          onEnd: () => this.end(),
        });
      }
      if (!this._mask) {
        this._mask = createMask(sectionEl);
      }
      if (!this._panel) {
        this._panel = createPanel(this._panelState(stop));
      }
    }

    _applyRevealState(sectionEl, stop, subIndex) {
      // subIndex === -1 means "first frame of this section" — show the
      // canvas only, no mask, no callout.
      if (subIndex < 0) {
        this._revealed = [];
        this._mask.setRevealed([]);
        this._canvas.setSubStep(0, this._subStepTotal(stop));
        if (this._callout) { this._callout.destroy(); this._callout = null; }
        return;
      }
      // Reveal up to subIndex.
      this._revealed = [];
      for (let i = 0; i <= subIndex; i++) {
        const pt = this._subStepPoint(stop, i);
        if (!pt) continue;
        const el = utils.getEl(pt.selector);
        if (el) this._revealed.push(el);
      }
      this._mask.setRevealed(this._revealed);
      this._canvas.setSubStep(this._revealed.length, this._subStepTotal(stop));
      if (this._callout) { this._callout.destroy(); this._callout = null; }
      const curPt = this._subStepPoint(stop, subIndex);
      const curEl = curPt ? utils.getEl(curPt.selector) : null;
      if (curPt && curEl) {
        const reduced = utils.reducedMotion();
        this._callout = createCallout(curEl, { text: curPt.label });
        if (reduced) {
          this._callout.root.style.animation = "none";
        }
      }
      this._reposition();
    }

    _panelState(stop) {
      const total = this._subStepTotal(stop);
      const done = Math.max(0, this._subIndex + 1);
      return {
        stepNumber: this._index + 1,
        totalSteps: this.stops.length,
        sectionTitle: stop.title,
        subStepDone: done,
        subStepTotal: total,
        canBack: this._index > 0 || this._subIndex > -1,
        canDoIt: total > 0,
        canNext: true,
        isPlaying: this._mode === "playing",
        isPaused: this._mode === "paused",
        onBack: () => this.back(),
        onDoIt: () => this.play(),
        onPause: () => this.pause(),
        onResume: () => this.resume(),
        onNext: () => this.next(),
        onEnd: () => this.end(),
      };
    }

    _refreshPanel() {
      if (!this._panel) return;
      this._panel.setState(this._panelState(this.stops[this._index]));
    }

    _reposition() {
      if (this._rafScheduled) return;
      this._rafScheduled = true;
      window.requestAnimationFrame(() => {
        this._rafScheduled = false;
        const stop = this.stops[this._index];
        const sectionEl = stop ? document.getElementById(stop.id) : null;
        if (!sectionEl) return;
        if (this._canvas) this._canvas.render();
        if (this._mask) this._mask.setRevealed(this._revealed);
        if (this._callout) this._callout.reposition();
      });
    }

    _onKeydown(e) {
      if (e.key === "Escape") { this.end(); return; }
      if (e.key === "ArrowRight" || e.key === " ") {
        if (this._mode === "playing") this.pause();
        else this.next();
        e.preventDefault();
      } else if (e.key === "ArrowLeft") {
        this.back();
        e.preventDefault();
      }
    }

    _injectStyles() {
      // See Task 8 — styles are injected here.
    }
  }
```

- [ ] **Step 1: Replace the existing `class SiteTour { ... }` with the orchestrator above**
- [ ] **Step 2: Commit**

```bash
git add docs/assets/js/tour.js
git commit -m "feat(tour): rewrite SiteTour orchestrator (state, lifecycle, play loop)"
```

---

### Task 8: Inject the new tour styles

**Files:**
- Modify: `docs/assets/js/tour.js` (`SiteTour._injectStyles()` method, which currently contains the long `<style>` block)

**Interfaces:**
- Consumes: nothing
- Produces: a single `<style id="tour-styles">` element appended to `<head>`, replacing today's contents

Replace the entire body of `_injectStyles()` (everything between the opening and closing backticks) with:

```js
      const style = document.createElement("style");
      style.id = "tour-styles";
      style.textContent = `
/* ── Tour canvas (first frame of each section) ── */
.tour-canvas {
  position: fixed;
  z-index: ${CONSTANTS.Z_HIGHLIGHT - 1};
  pointer-events: none;
  border-radius: 22px;
  outline: 1.5px solid rgba(104, 172, 229, 0.35);
  outline-offset: 0;
  transition: outline-color 0.2s ${CONSTANTS.SMOOTH};
  animation: tour-canvas-in 0.4s ${CONSTANTS.SMOOTH} both;
}
.tour-canvas__pill {
  position: absolute;
  top: -14px;
  left: 16px;
  padding: 4px 12px;
  border-radius: 9999px;
  background: var(--apple-primary, #002D72);
  color: #fff;
  font-size: 11.5px;
  font-weight: 600;
  letter-spacing: 0.02em;
  pointer-events: auto;
  box-shadow: 0 4px 12px -4px rgba(4, 8, 18, 0.4);
}
.tour-canvas__strip {
  position: absolute;
  top: -2px;
  left: 50%;
  transform: translateX(-50%);
  display: flex;
  gap: 4px;
  padding: 2px 8px;
  background: rgba(6, 10, 22, 0.85);
  border-radius: 9999px;
  pointer-events: auto;
}
.tour-canvas__seg {
  width: 14px;
  height: 3px;
  border-radius: 2px;
  background: rgba(255, 255, 255, 0.18);
  transition: background 0.3s ${CONSTANTS.SMOOTH};
}
.tour-canvas__seg.is-done {
  background: rgba(104, 172, 229, 0.95);
}
.tour-canvas__end {
  position: absolute;
  top: -14px;
  right: 16px;
  padding: 4px 12px;
  border-radius: 9999px;
  border: 1px solid rgba(0, 45, 114, 0.25);
  background: rgba(255, 255, 255, 0.85);
  color: var(--apple-primary, #002D72);
  font-family: inherit;
  font-size: 11.5px;
  font-weight: 600;
  cursor: pointer;
  pointer-events: auto;
  transition: background 0.15s ${CONSTANTS.SMOOTH}, transform 0.15s ${CONSTANTS.SMOOTH};
}
.tour-canvas__end:hover {
  background: rgba(104, 172, 229, 0.18);
  transform: translateY(-1px);
}
@keyframes tour-canvas-in {
  from { opacity: 0; transform: scale(0.992); }
  to   { opacity: 1; transform: scale(1); }
}

/* ── Tour mask (SVG cutouts) ── */
.tour-mask-svg {
  position: absolute;
  inset: 0;
  z-index: ${CONSTANTS.Z_MASK};
  pointer-events: none;
  backdrop-filter: blur(2px);
  -webkit-backdrop-filter: blur(2px);
}
.tour-mask-svg rect.hole {
  transition: rx ${CONSTANTS.MASK_HOLE_BLOOM_MS}ms ${CONSTANTS.SPRING},
              ry ${CONSTANTS.MASK_HOLE_BLOOM_MS}ms ${CONSTANTS.SPRING};
}
.tour-mask-svg rect.hole--blooming {
  animation: tour-hole-bloom ${CONSTANTS.MASK_HOLE_BLOOM_MS}ms ${CONSTANTS.SPRING} both;
}
@keyframes tour-hole-bloom {
  from { rx: 4; ry: 4; }
  to   { rx: 12; ry: 12; }
}

/* ── Tour callout ── */
.tour-callout {
  position: fixed;
  z-index: ${CONSTANTS.Z_CALLOUT};
  width: min(220px, calc(50vw - 48px));
  padding: 10px 14px;
  pointer-events: auto;
  animation: tour-callout-in-right ${CONSTANTS.CALLOUT_SPRING_MS}ms ${CONSTANTS.SPRING} both;
}
.tour-callout[data-side="left"] {
  animation-name: tour-callout-in-left;
}
.tour-callout__text {
  margin: 0;
  font-size: 12.5px;
  line-height: 1.4;
  color: var(--apple-text-primary, inherit);
}
@keyframes tour-callout-in-right {
  0%   { opacity: 0; transform: translateX(12px) scale(0.96); }
  100% { opacity: 1; transform: translateX(0) scale(1); }
}
@keyframes tour-callout-in-left {
  0%   { opacity: 0; transform: translateX(-12px) scale(0.96); }
  100% { opacity: 1; transform: translateX(0) scale(1); }
}

/* ── Tour panel (bottom-right) ── */
.tour-panel {
  position: fixed;
  right: 20px;
  bottom: 20px;
  z-index: ${CONSTANTS.Z_PANEL};
  width: min(360px, calc(100vw - 40px));
  padding: 16px 18px;
  display: flex;
  flex-direction: column;
  gap: 6px;
}
.tour-panel__progress {
  font-size: 11.5px;
  font-weight: 600;
  letter-spacing: 0.04em;
  text-transform: uppercase;
  color: var(--apple-primary-on-dark, #68ACE5);
  opacity: 0.85;
}
.tour-panel__title {
  font-family: var(--font-display, inherit);
  font-size: 16px;
  font-weight: 700;
  color: var(--apple-text-primary, inherit);
}
.tour-panel__dots {
  display: flex;
  gap: 5px;
  margin: 2px 0 4px;
}
.tour-panel__dot {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: rgba(0, 45, 114, 0.18);
  transition: background 0.3s ${CONSTANTS.SMOOTH}, transform 0.3s ${CONSTANTS.SPRING};
}
.tour-panel__dot.is-done {
  background: var(--apple-primary, #002D72);
  transform: scale(1.2);
}
.tour-panel__controls {
  display: flex;
  align-items: center;
  gap: 6px;
  margin-top: 6px;
  flex-wrap: wrap;
}
.tour-panel__spacer {
  flex: 1 1 auto;
}
.tour-btn {
  font-family: inherit;
  font-size: 12.5px;
  font-weight: 600;
  padding: 7px 14px;
  border-radius: 9999px;
  border: 1px solid transparent;
  cursor: pointer;
  transition: transform 0.15s ${CONSTANTS.SMOOTH}, background 0.15s ${CONSTANTS.SMOOTH}, box-shadow 0.2s ${CONSTANTS.SMOOTH};
}
.tour-btn:hover { transform: translateY(-1px); }
.tour-btn--primary {
  background: var(--apple-primary, #002D72);
  color: #fff;
  animation: tour-next-pulse 2.2s ease-in-out infinite;
}
.tour-btn--primary:hover {
  background: var(--apple-primary-focus, #1a3d8f);
  animation-play-state: paused;
}
.tour-btn--ghost {
  background: transparent;
  border-color: rgba(0, 45, 114, 0.25);
  color: var(--apple-primary, #002D72);
}
.tour-btn--ghost:hover { background: rgba(0, 45, 114, 0.06); }
.tour-btn--doit {
  background: rgba(104, 172, 229, 0.12);
  border-color: rgba(104, 172, 229, 0.4);
  color: var(--apple-primary-focus, #1a3d8f);
}
.tour-btn--doit:hover { background: rgba(104, 172, 229, 0.22); }
@keyframes tour-next-pulse {
  0%, 100% { box-shadow: 0 0 0 0 rgba(104, 172, 229, 0.45); }
  50%      { box-shadow: 0 0 0 6px rgba(104, 172, 229, 0); }
}

/* ── Take-a-Tour CTA breathing ── */
.tour-cta {
  position: relative;
  animation: tour-cta-breathe 3.6s cubic-bezier(0.45, 0, 0.55, 1) infinite;
}
.tour-cta:hover {
  animation-play-state: paused;
  box-shadow: 0 0 0 4px rgba(104, 172, 229, 0.22);
}
@keyframes tour-cta-breathe {
  0%, 100% { transform: scale(1); box-shadow: 0 0 0 0 rgba(104, 172, 229, 0.28); }
  50%      { transform: scale(1.015); box-shadow: 0 0 0 5px rgba(104, 172, 229, 0.12); }
}

@media (prefers-reduced-motion: reduce) {
  .tour-canvas,
  .tour-mask-svg rect.hole--blooming,
  .tour-callout,
  .tour-btn--primary,
  .tour-cta {
    animation: none !important;
    transition: none !important;
  }
}

@media (max-width: 640px) {
  .tour-panel {
    left: 12px;
    right: 12px;
    bottom: 12px;
    width: auto;
  }
}
      `;
      document.head.appendChild(style);
```

- [ ] **Step 1: Replace the body of `_injectStyles()` with the new CSS**
- [ ] **Step 2: Commit**

```bash
git add docs/assets/js/tour.js
git commit -m "feat(tour): inject new tour styles (canvas, mask, callout, panel)"
```

---

### Task 9: Manual smoke test

**Files:** none

This task has no automated test. The plan author manually verifies the tour behaves per the spec.

- [ ] **Step 1: Start a local server**

```bash
cd /Users/alina/Library/CloudStorage/OneDrive-JohnsHopkins/Research/26ARIA/daily/06-06/ARIA
python3 -m http.server --directory docs 8765
```

- [ ] **Step 2: Open `http://localhost:8765/` in Chrome and Safari**

- [ ] **Step 3: Click the "Take a Tour" button and verify:**
  - [ ] First frame shows the first section in its full natural layout, with a "Tour mode" pill in the top-left, a progress strip, and an "End Tour" pill top-right.
  - [ ] No scrim, no mask, no spotlight.
  - [ ] Bottom-right panel shows `Step 1 of 9` (or whatever the current stop count is) with the section title.

- [ ] **Step 4: Click "Next ▸" 3 times and verify:**
  - [ ] First click: a soft dark mask covers the section, with a rounded-rect hole over the first element. The element has a subtle pulse / breath.
  - [ ] A glass callout bubble flows in next to the revealed element (spring-in animation).
  - [ ] Second click: another element is revealed (hole is added to the mask), a new callout replaces the old one.
  - [ ] Third click: same, accumulating reveals.
  - [ ] Sub-step progress strip in the canvas frame updates (filled segments increase).
  - [ ] Sub-step dots in the panel update (filled dots increase).

- [ ] **Step 5: Click "Do it for me ▶" and verify:**
  - [ ] Button morphs to "⏸ Pause".
  - [ ] Tour plays through the remaining elements at ~1s each.
  - [ ] Elements that have an `action` (e.g. `<details>` summary, `.tunneling-example-btn`, `.tr-run-btn`) get clicked/opened — verify by looking at the section state.
  - [ ] After the section is fully played, the panel shows "Next ▸" and the play loop stops.

- [ ] **Step 6: Click "Pause" mid-play and verify:**
  - [ ] Button morphs to "▶ Resume".
  - [ ] Reveal state stays where it is.
  - [ ] Click "Resume" → playback continues from the next element.

- [ ] **Step 7: Advance through 2–3 sections and verify:**
  - [ ] Each new section starts with the full canvas (no mask).
  - [ ] All callouts and mask holes from the previous section are cleaned up.
  - [ ] `onEnter` / `onLeave` still work (the `kg-section` stop should auto-open its `<details>`).

- [ ] **Step 8: Test keyboard:**
  - [ ] `→` advances one sub-step (or pauses if playing).
  - [ ] `←` goes back one sub-step.
  - [ ] `Space` toggles play/pause.
  - [ ] `Esc` ends the tour cleanly.

- [ ] **Step 9: Test reduced motion:**
  - In Chrome DevTools → Rendering → "Emulate CSS media feature prefers-reduced-motion: reduce" → reload.
  - Verify: no spring/bloom animations; mask still works; progress dots still update; playback still works.

- [ ] **Step 10: Test resize:**
  - During play, resize the window from 1440px wide down to 600px wide.
  - Verify: canvas + mask re-anchor; callout reposition.

- [ ] **Step 11: Commit any final tweaks**

```bash
git add docs/assets/js/tour.js
git commit -m "fix(tour): post-smoke tweaks"
```

(Only if the smoke test surfaced issues. Otherwise skip the commit.)

---

### Task 10: Update `CLAUDE.md` and visual smoke screenshots

**Files:**
- Modify: `docs/CLAUDE.md` (does not exist — the spec mentions a `docs/CLAUDE.md` may be added in the future; skip if absent)
- Create: `.tmp-screenshots/tour-v2-*.png` (temporary visual reference; matches the existing `.tmp-screenshots/` convention in this repo's working tree)

**Why this is the last task:** the spec's testing section is "manual smoke + visual screenshot pass". The screenshot pass is its own task so it's reviewable.

- [ ] **Step 1: Take 4 screenshots at 1440, 1024, 768, 390 wide for the first 3 stops**

```bash
# Use Chrome DevTools' "Capture node screenshot" via the chrome-devtools MCP,
# or simply resize the window to each width and take a viewport screenshot
# at: first frame of stop 1, after 1st Next of stop 1, after Do-it-for-me of stop 1.
# Save to:
.tmp-screenshots/tour-v2-1440-stop1-first.png
.tmp-screenshots/tour-v2-1440-stop1-revealed.png
.tmp-screenshots/tour-v2-1440-stop1-played.png
# (repeat for stop 2, stop 3)
# (repeat at 1024, 768, 390)
```

- [ ] **Step 2: Visually confirm:**
  - [ ] No element overlap or text being eaten by the callout.
  - [ ] Mask holes are correctly aligned over each revealed element at every width.
  - [ ] Panel doesn't overlap section content at 390px wide.
  - [ ] Canvas frame pill ("Tour mode · Step 3/9 · ...") fits within the section's left margin at 390px.

- [ ] **Step 3: If any width shows a layout issue, fix it (likely a Task 8 CSS tweak)**

```bash
git add docs/assets/js/tour.js
git commit -m "fix(tour): responsive layout tweaks"
```

(Only if changes were needed.)

- [ ] **Step 4: Final commit + summary**

```bash
git log --oneline website/index-arrangement-fix ^main
# Review the last 8-10 commits — should show the guided-tour-v2 progression
```

---

## Self-Review

**1. Spec coverage:**
- §1 Problem: addressed by Tasks 7-8 (rewrite) ✓
- §2 Goals: Task 3 (canvas first frame), Task 4 (mask + reveal), Task 7 (Do-it-for-me timeline), all together ✓
- §3 Non-goals: no `index.html` change (Task 1 modifies only `tour.js`), no deps ✓
- §4 Architecture: Task 2 (CONSTANTS, utils), Task 3 (canvas renderer), Task 4 (mask renderer), Task 5 (callout renderer), Task 6 (panel renderer), Task 7 (orchestrator) ✓
- §5 Visual treatment: Task 3 (canvas chrome), Task 4 (mask SVG + bloom), Task 5 (callout spring), Task 8 (motion CSS) ✓
- §6 Per-element actions: Task 1 (data shape), Task 7 (action dispatch in `play()`) ✓
- §7 Playback cadence: Task 7 (`PLAY_*` constants in Task 2, applied in `play()`) ✓
- §8 Edge cases: Task 7 handles 1, 5, 6, 7; Task 8 handles 4; Task 9 step 10 handles 3 ✓
- §9 Keyboard: Task 7 (`_onKeydown`) ✓
- §10 Files: only `docs/assets/js/tour.js` ✓
- §11 Testing: Task 9 (manual smoke), Task 10 (visual screenshots) ✓
- §12 Risks: Task 7 spam guard (`_isAdvancing`), Task 7 cancel (`_cancelPlay`) ✓

**2. Placeholder scan:** No "TBD", no "similar to Task N", every code step shows full code, every test step shows what to verify. ✓

**3. Type consistency:** `createCanvasFrame`, `createMask`, `createCallout`, `createPanel` all return objects with the `{root, destroy(), ...}` shape called out in their interfaces. `_subStepTotal`, `_subStepPoint`, `_currentSubStepEl`, `_panelState` are referenced consistently. The `action.kind` values are: `"click" | "open-details" | "change"` — Task 1 (data) and Task 7 (dispatch) use the same set. ✓
