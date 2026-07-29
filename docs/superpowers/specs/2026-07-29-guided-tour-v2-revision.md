# Guided Site Tour v2 — Revision (delta from approved 2026-07-29 spec)

**Date:** 2026-07-29 (later same day)
**Status:** Approved (user)
**Scope:** delta over the existing approved spec; the prior spec remains authoritative except where this document overrides it.

## Why this revision

The approved spec models each section as a sequence of "sub-steps" the user advances one-by-one with the panel **Next** button. The user now wants a different mental model:

- A **section is one step**, not many.
- Inside a section, the user sees **all clickable elements at once**, each with a numbered/lettered label and a breathing ring inviting a click.
- The user **clicks each hole themselves** (or hits "Do it for me" to automate the same sequence).
- After all holes are clicked, the section returns to **fully clear for ~3s**, then the panel **Next** pulses to prompt the next section.

This is closer to how Apple/Keynote "guided tours" actually work: one "frame" per section, with all interactive hotspots visible simultaneously, labeled, and breathing.

## What changes

### Per-section timeline (replaces the "sub-step" model in the approved spec)

```
[t = 0s]     Section enters.  Section is FULLY CLEAR (no mask, no holes, no callouts).
              Bottom-right panel shows section title + dots + "Next" (idle, breathing).

[t = 2s]     Mask fades in. ALL clickable holes appear simultaneously,
              each with:
                - a rounded-rect cutout in the SVG mask
                - a small numbered/lettered chip (1, 2, 3, ... or a, b, c, ...)
                  connected by a DASHED line to the target
                - a soft breathing ring (pulsing) inviting a click
              User can click any hole in any order. The panel "Next" is now
              GHOSTED and a "Do it for me" button appears in the primary slot.

[user clicks a hole, OR presses "Do it for me"]
              The clicked hole's action fires (open-details / click / change).
              The hole's breathing stops; its dashed label fades out.
              The hole stays visible (the section is still partially masked).

[all holes clicked]
              All breathing stops. Mask fades out over ~400ms.
              Section returns to FULLY CLEAR for ~3s (a "breath" beat — the
              user gets to see what they've activated, e.g. expanded <details>,
              routed query, etc.). No callouts during this beat.

[after 3s]   Panel "Next" begins to BREATHE (pulsing) to prompt the user.

[user clicks Next, OR presses → / Space]
              Advance to next section. Repeat from t=0.

[user clicks End / Esc]
              Tour ends cleanly.
```

### Data model (same `STOPS`, repurposed)

- `focusPoints[]` is the **list of clickable holes** in this section (not a sub-step sequence).
- `actionPoint` is treated as the **last** entry in the holes list (no separate concept).
- Each entry's existing `action` field still drives `open-details` / `click` / `change`.
- New optional `label` field on each entry — a string to render in the chip. If absent, the renderer auto-numbers 1, 2, 3, ...

### Removed / simplified

- **No sub-step index.** `_subIndex` and "sub-step progress strip" in the canvas frame go away. The canvas pill still shows "Step N of M · section title" but no sub-step dots.
- **No mid-section Next.** The panel "Next" is disabled (ghosted) while any hole is unclicked. It only becomes the primary action once all holes are clicked and the clear-frame beat has elapsed.
- **No "Pause/Resume" UI.** "Do it for me" runs to completion (or is canceled by clicking the same button again, which becomes "Skip" while it's playing). Simpler than the prior play/pause/resume triad.

### Renderers

- `createCanvasFrame` — same as before, but loses the sub-step progress strip and gains a single thin line under the pill that says "Click the highlighted element" (or disappears once the section's clear-frame beat is over).
- `createMask` — same SVG-mask primitive. New: `setRevealed(els, opts)` where `opts.label` is either `"1, 2, 3"` or `"a, b, c"` per the stop's `labels` field. Holes are placed on initial reveal and **stay** until cleared.
- `createHoleLabel` (NEW) — small chip + dashed leader line for each hole. Replaces the old callout bubbles. The chip shows "1" / "2" / "a" / etc.
- `createCallout` — **no longer used** in this revision. The hole labels carry the explanatory text via the chip's tooltip on hover. (The old `createCallout` function can stay for backward compat or be removed.)
- `createPanel` — same, but the primary slot logic is:
  - Idle, holes still pending → `[ Do it for me ▶ ]` (primary, breathing)
  - Idle, holes done, in clear-beat → `[ Next ▸ ]` (primary, breathing)
  - Playing "Do it for me" → `[ Skip ▸▸ ]` (primary)
  - Always: `[ End ]` (ghost)

### Motion

- **Hole breathing**: `box-shadow` ring animates 0 → 8px → 0 over 2.0s, sine ease, infinite, paused when the hole is clicked.
- **Mask fade-in**: dark layer opacity 0 → 0.45 over 380ms on initial reveal of all holes.
- **Mask fade-out**: opacity 0.45 → 0 over 400ms after all holes clicked.
- **Chip in**: `scale(0.8) → scale(1)` with a 320ms spring.
- **Reduced motion**: breathing becomes a static outline, no scale, no opacity pulses.

### What stays the same

- One file: `docs/assets/js/tour.js`.
- No `index.html` change, no CSS files, no new deps.
- The `STOPS` data with `action` field.
- The orchestrator pattern (state, lifecycle, keyboard).
- The mask SVG technique.

## Open question (will pick default)

- **Numbering style**: number (1, 2, 3…) or letter (a, b, c…). **Default:** numbers. Easy to flip per-stop with an optional `labels: "letters"` field on a stop.

## Implementation plan (sketch)

1. Re-scope `_subIndex` → `_holesDone` (a Set or counter of clicked holes). Drop sub-step progress strip.
2. Re-scope `next()` so it only fires when the current section is in the "ready to advance" state. Otherwise the click is a no-op (or shows a brief "click all hotspots first" pulse).
3. Add `_scheduleReveal()` — after entering a section, wait 2s, then call `_revealAllHoles()` which builds the mask + holes + labels simultaneously.
4. Add `_clearMask()` — fade out the mask and labels after the last hole is clicked, set a 3s timer, after which the panel "Next" starts breathing.
5. Replace `createCallout` usage with a new `createHoleLabel(targetEl, label, text)` that draws the chip + dashed SVG line.
6. Update panel render to reflect the new primary-slot states.
7. Update keyboard: `→` / `Space` advance only when ready; `Esc` ends.

## What gets deleted

- `_subStepTotal`, `_subStepPoint`, `_currentSubStepPoint`, `_currentSubStepEl` (folded into `_holes` list).
- `play()`, `pause()`, `resume()`, `isPlaying()` — replaced by a simpler `autoPlay()` / `skipAutoPlay()` pair.
- The sub-step progress strip in the canvas frame.
- The sub-step dots in the panel.
