# Guided Site Tour v2 — Design

**Date:** 2026-07-29
**Status:** Approved (user)
**Author:** brainstorm session

## 1. Problem

The current "Take a Tour" overlay (in `docs/assets/js/tour.js`) is functionally
complete but visually immature. It:

- Drops a full-viewport scrim + section outline as soon as the tour starts,
  which feels like a modal rather than a guided walkthrough.
- Jumps section-to-section on every "Next" press with no in-section flow.
- "Do it for me" calls `el.click()` then `this.next()`, so it skips the page
  instead of playing through the section.
- Lacks the calm, slightly-springy "q弹" pacing of the rest of the site
  (which targets Apple-style aesthetics throughout `docs/assets/css/*.css`).

## 2. Goals

1. **Show the whole canvas first.** When the tour enters a section, the user
   sees the section in its natural, un-tourified layout — only a thin
   "Tour mode" frame and a sub-step progress strip are added on top.
2. **Reveal elements one at a time with a "hollow-out" rhythm.** Each Next
   press "uncovers" one element against a soft dark mask, with a springy
   bloom that matches the site's overall feel.
3. **Make "Do it for me" actually play through the section.** At ~1s/element,
   it lights each element, fires its action (open a `<details>`, click a
   button, etc.), and pauses at the end of the section.
4. **Stay within Approach B** — preserve the `STOPS` data model, rewrite the
   rendering, no other files touched.

## 3. Non-goals

- No new dependencies (no new libraries, no build step).
- No changes to `index.html` (data lives in `tour.js`).
- No automated test infrastructure; this is presentation-only JS.
- No changes to other demo widgets (`tier-router`, `kg-explorer`, etc.).
- No internationalization changes; English copy only.

## 4. Architecture

Three layers, one job each:

1. **Data layer (unchanged shape).** `STOPS` in `tour.js` keeps
   `{ id, title, body, focusPoints[], actionPoint, onEnter, onLeave }`.
   `focusPoints[]` is reinterpreted as the **per-element reveal sequence**
   for that section. `actionPoint` is the **final, "try this" element**.
2. **Orchestrator.** A rewritten `SiteTour` class drives the tour lifecycle,
   the per-section sub-step index, the "play mode" timeline, keyboard, and
   per-frame positioning.
3. **Renderers (new, swappable).** Three small render functions, each with
   co-located CSS injected by the orchestrator:
   - `renderCanvasFrame(sectionEl, stepMeta)` — rounded "Tour mode" overlay
     hugging the section, with a corner pill (`Tour mode · Step 3/9 ·
     PSP Hierarchy`) and a sub-step progress strip.
   - `renderMask(sectionEl, revealedEls[])` — a single `<svg>` overlay
     clipped to the section's bounding rect. The svg contains a dark glass
     layer with **rounded-rect cutouts** (drawn into an SVG `<mask>`) for
     every currently-revealed element.
   - `renderCallout(targetEl, text)` — small glass bubble that flows in next
     to its target with a spring transition. Replaces today's
     SVG-connector callouts.

### Data flow per "Next" press

```
SiteTour.advanceSubStep()
  ├─ if first sub-step of this section:
  │     renderCanvasFrame(); section stays fully visible (no mask yet)
  ├─ else:
  │     revealedEls.push(currentSubStepEl)
  │     renderMask(sectionEl, revealedEls)
  │     renderCallout(currentSubStepEl, currentSubStepLabel)
  └─ if last sub-step: panel shows "✓ Done — Next ▸"
```

### "Do it for me" timeline

```
SiteTour.play()
  ├─ mask = full (nothing lit)
  ├─ for i = 0..n-1:
  │   revealedEls.push(subStepEls[i])
  │   renderMask(); renderCallout()
  │   await sleep(600ms)                    // spring-in finishes
  │   if subStepEls[i].action: fireAction()  // click / open-details
  │   await sleep(400ms)                    // post-action beat
  ├─ on done: state = "section-done"
  └─ user can call pause() / resume() / end() at any time
```

## 5. Visual treatment

### First frame of each section ("the canvas")
- Rounded outline hugging the section: `border-radius: 22px`, 1.5px stroke
  in `var(--apple-primary-on-dark)` at 35% opacity.
- A small pill in the top-left: `Tour mode · Step 3/9 · PSP Hierarchy`.
- A thin progress strip below the pill: `▰▰▰▱▱▱▱`.
  Filled = revealed, empty = pending.
- A small "End Tour ✕" ghost button in the top-right of the canvas.
- Everything else: untouched, no scrim, no mask, no spotlight.
- The main control panel (bottom-right) keeps its position and "Next ▸" CTA.

### Mask system (after first Next)
- A single `<svg>` overlay, `position: absolute; inset: 0`, clipped to the
  section's bounding rect via `clip-path: inset(...)` so it never bleeds
  into other sections.
- Inside the SVG: one `<rect>` filling the section in
  `rgba(6,10,22,0.45)` with `backdrop-filter: blur(2px)`.
- One `<rect>` per revealed element drawn in white into an SVG `<mask>`,
  so the dark layer is truly punched through.
- Each revealed element also gets a thin pulsing outline (`box-shadow`
  ring) and a soft "breath" via `transform: scale(1.0→1.015→1.0)` at
  2.4s with sine ease.

### Per-element reveal animation
- **Spring-in:** `opacity 0→1, transform scale(0.94→1.02→1)` over 420ms
  with `cubic-bezier(0.34, 1.56, 0.64, 1)`.
- **Mask hole expansion:** the SVG hole's `rx`/`ry` interpolates from
  `4` → `12` over 280ms (rounded corners "bloom" outward).
- **Callout entrance:** from the side nearest the free space;
  `translateX(±12px) + scale(0.96) → identity` over 320ms spring.
- **Reduced motion:** falls back to instant fade with no transform.

### Inter-element transitions
- Reveals are **accumulating** — previously-revealed elements stay lit
  when a new one is added.
- The mask only ever grows holes; it never animates holes shrinking,
  which keeps the visual continuous and prevents flicker.
- Callouts for the *previous* element are removed (so the panel stays
  uncluttered) before the new callout renders.

### Panel (bottom-right) updates
- Header: `Step 3/9 · The PSP Hierarchy` (was just the title).
- Sub-progress dots: `● ● ● ○ ○ ○` (filled = revealed).
- Buttons:
  - Always-present: `[ ◀ Back ]` (ghost), `[ End Tour ]` (ghost)
  - Primary slot (morphs based on state):
    - Idle, no elements played yet → `[ Do it for me ▶ ]` (primary, pulses)
    - Idle, partially played → `[ Next ▸ ]` (primary)
    - Section fully revealed (last step done) → `[ Next ▸ ]` (primary, label: `Next: <next-section-title> ▸`)
    - Playing → `[ ⏸ Pause ]` (primary)
    - Paused mid-play → `[ ▶ Resume ]` (primary)
  - "Do it for me" appears as a secondary button when not in the primary slot.
- `prefers-reduced-motion`: springs become instant fades; progress dots
  still update; mask still works (it's not motion).

## 6. Per-element actions (extended data)

Each entry in `focusPoints[]` (and `actionPoint`) gains an optional
`action` field. Three action kinds, all opt-in:

```js
{
  selector: "#problem .tunneling-example-btn:nth-of-type(2)",
  label: "Try Example 2 — the same failure mode, on a different query.",
  action: { kind: "click" }      // just .click() the element
}
```

```js
{
  selector: "#kg-section details.detail-toggle summary",
  label: "Open Advanced settings to see exactly which KG this demo loads.",
  action: { kind: "open-details" }   // set <details>.open = true
}
```

```js
{
  selector: "#tier-deep-dive .tier-2-detail summary",
  label: "Expand to see ARIA validate physical constraints...",
  action: { kind: "open-details" }
}
```

If an element has no `action`, "Do it for me" still highlights it and
shows its callout, but doesn't fire a click — static explanatory
elements just get the spotlight treatment.

`onEnter` and `onLeave` keep working (used today for the `details` panel
open/close in the KG section).

## 7. Playback (Do it for me)

- `cadenceMs = 1000` (≈1s/element, per the user's brief).
  - 360ms spring-in beat
  - 100ms pause
  - fire action (or skip if none)
  - 360ms post-action beat
  - 180ms gap to next iteration
  - (Total per-element ≈1.0s with an action; ≈0.7s without.)
- During play, the "Do it for me" button morphs into a `[ ⏸ Pause ]`
  ghost button. Hitting it cancels the loop; the button then shows
  `[ ▶ Resume ]` in its place.
- After the section is fully played, the panel shows
  `[ ✓ Done — Next ▸ ]` and waits for the user.
- User-spam-guard: `_isAdvancing` boolean; at most one click is queued.

## 8. Edge cases

1. **Stops with no `focusPoints` and no `actionPoint`** (e.g. `#robustness`):
   single full-section spotlight + single callout, "Do it for me" is hidden.
2. **Section scrolled out of view mid-tour**: canvas + mask re-anchor via
   `getBoundingClientRect` on resize and scroll (rAF-throttled, same as
   today). "Next" also calls `scrollIntoView({behavior:'smooth', block:'center'})`
   if the section is more than 30% off-screen.
3. **Small screens (< 720px)**: canvas frame becomes full-width with a 12px
   outer margin; the bottom-right panel docks to a bottom sheet
   (full-width, same as current `max-width: 640px` breakpoint). The SVG
   mask still works (we re-measure on resize).
4. **Reduced motion**: spring transforms become instant fades; mask still
   works (it's not motion). Progress dots still update.
5. **User clicks outside the panel during play**: ignored. User can hit
   `Esc` to end the tour or `Space` to toggle Play/Pause.
6. **Action fires on real `<details>`/`<button>`** that have side effects
   (e.g. the tier router routing an example query): this is the intended
   behavior. Side effects are the *point* of "Do it for me".
7. **Mask performance with many revealed elements**: cap active hole count
   by only rendering the current hole + previously-revealed ones
   (typically ≤ 5). Acceptable for the site.

## 9. Keyboard

- `→` / `Space` — Next sub-step (or Pause/Resume during play)
- `←` — Back
- `Esc` — End tour

## 10. Files changed

| File                  | Change                                                                  |
|-----------------------|-------------------------------------------------------------------------|
| `docs/assets/js/tour.js` | Rewrite `SiteTour` (orchestrator + renderers). Keep `STOPS` mostly intact, just add `action` fields where needed (about 6 entries). Keep all `_injectStyles` content; restructure into named CSS strings per renderer so styles stay co-located with the JS that uses them. |

No CSS file changes, no new dependencies, no `index.html` change.
Roughly **+500 / −200 lines** in `tour.js`, all behind a single IIFE,
no globals leaked.

## 11. Testing strategy

1. **Manual smoke pass** in Chrome + Safari (the page already targets
   Apple-style rendering):
   - Start tour → first section shows full canvas, no mask
   - Click Next 3× → elements bloom in one by one, mask grows, callouts appear
   - Click "Do it for me" → plays through section at ~1s cadence, fires actions
   - Pause mid-play → elements stay where they are, button shows Resume
   - Click an action element manually (e.g. `<details>`) → state stays consistent
   - Reach end of section → panel shows "Done — Next"
   - Advance to next section → first frame is the whole new section
   - Resize window during play → canvas + mask re-anchor
   - Toggle `prefers-reduced-motion: reduce` → springs become instant fades
2. **Visual screenshot pass** at the 4 viewport sizes the rest of the site
   is checked at (1440, 1024, 768, 390 wide), for the first 3 stops.
3. **No automated tests** — this is presentation-only JS with no business
   logic. Matches the rest of the demo site (no unit tests for its
   interactive JS either).

## 12. Risks & mitigations

- **Mask SVG performance** with many revealed elements → cap active hole
  count, render only current + previously-revealed (≤ 5). Acceptable.
- **Reveal race** if user spams Next → guard with `_isAdvancing` boolean;
  queue one click at most.
- **Action fires on real `<details>`/`<button>`** with side effects →
  intentional; user said "actually click those buttons".

## 13. Open questions

None — all design questions were resolved during brainstorming.
