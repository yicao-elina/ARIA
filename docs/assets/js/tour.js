/**
 * tour.js — Guided, operational walkthrough of the ARIA site.
 *
 * v2 (2026-07-29): rewritten as a section-as-canvas tour.
 *   - First frame of each section shows the section in its natural layout,
 *     with a thin "Tour mode" frame, sub-step progress strip, and End button.
 *   - Each "Next" press "un-covers" one element against an SVG mask with
 *     springy bloom and a flowing callout.
 *   - "Do it for me" plays through the section at ~1s/element, firing
 *     each element's action (click / open-details / change).
 *   - Pause / Resume / Back / Next all work mid-play.
 *   - Reduced-motion, keyboard, and responsive resize all honored.
 *
 * Self-contained page chrome. No dependencies. Self-initializes on
 * DOMContentLoaded (guarded for the case the script executes after
 * the event already fired, since it is loaded with `defer`).
 */
(function () {
  "use strict";

  // ════════════════════════════════════════════════════════════════
  // DATA: stops
  // ════════════════════════════════════════════════════════════════
  const STOPS = [
    {
      id: "problem",
      title: "The Problem: Contextual Tunneling",
      body: "Compare a baseline LLM against a naive KG+LLM system below — the naive system over-anchors on partial evidence. Try the demo to see the failure mode ARIA is built to prevent.",
      focusPoints: [
        {
          selector: "#problem .tunneling-panel--naive-kg .tunneling-segment--error",
          label: "This is contextual tunneling: a plausible-sounding claim built by over-anchoring on partial KG evidence.",
        },
        {
          selector: "#problem .tunneling-panel--baseline",
          label: "The baseline LLM, using only parametric knowledge, avoids this trap — but has no causal grounding at all.",
        },
      ],
      actionPoint: {
        selector: "#problem .tunneling-example-btn:nth-of-type(2)",
        label: "Try Example 2 to see the same failure mode show up on a different query.",
        action: { kind: "click" },
      },
    },
    {
      id: "psp",
      title: "The PSP Hierarchy",
      body: "Processing, Structure, and Property form the causal backbone ARIA reasons over. Hover the nodes in the diagram below to see how each layer connects.",
    },
    {
      id: "cascade",
      title: "Three-Tier Adaptive Cascade",
      body: "This is ARIA's core mechanism. Try clicking “Route Query” or one of the example pills below to watch a query get routed through Tier 1, 2, or 3 based on causal completeness.",
      focusPoints: [
        {
          selector: "#cascade .tr-example-btns .tr-example-btn",
          label: "Each pill is a worked example — click one to route it through a different tier.",
          action: { kind: "click" },
        },
      ],
      actionPoint: {
        selector: "#cascade .tr-run-btn",
        label: "Click “Route Query” to send this example through the three-tier cascade.",
        action: { kind: "click" },
      },
    },
    {
      id: "kg-section",
      title: "Knowledge Graph Explorer",
      body: "Explore the interactive causal knowledge graph — filter by material, PSP layer, or edge type. We've also opened the “Advanced settings” panel below the graph, which discloses exactly which KG file this demo loads.",
      focusPoints: [
        {
          selector: "#kg-section svg.kg-svg",
          label: "Nodes are PSP entities — hover any node to trace its causal connections.",
        },
      ],
      actionPoint: {
        selector: "#kg-section .kg-filter-material",
        label: "Try switching materials — the graph re-filters to just that system's PSP edges.",
        action: { kind: "change" },
      },
      onEnter(section) {
        const details = section.querySelector("details.detail-toggle");
        if (details && !details.open) {
          details.setAttribute("data-tour-reopen", "1");
          details.open = true;
        }
      },
      onLeave(section) {
        const details = section.querySelector("details.detail-toggle[data-tour-reopen]");
        if (details) {
          details.open = false;
          details.removeAttribute("data-tour-reopen");
        }
      },
    },
    {
      id: "tier-deep-dive",
      title: "Tier-by-Tier Deep Dives",
      body: "Each tier has a worked example. Try expanding one of the “Example” panels below to see a full reasoning trace for that tier.",
      focusPoints: [
        {
          selector: "#tier-deep-dive .tier-1-detail summary",
          label: "This one's already open — see the full causal trace from processing to property below.",
          action: { kind: "open-details" },
        },
        {
          selector: "#tier-deep-dive .tier-3-detail summary",
          label: "This example honestly flags low confidence instead of guessing with false certainty.",
          action: { kind: "open-details" },
        },
      ],
      actionPoint: {
        selector: "#tier-deep-dive .tier-2-detail summary",
        label: "Expand this one to see ARIA validate physical constraints before transferring MoS₂'s mechanism to MoSe₂.",
        action: { kind: "open-details" },
      },
    },
    {
      id: "results",
      title: "Results",
      body: "The full benchmark results — chart and table — live here. Worth a scan, but we'll keep moving since the next sections are more hands-on.",
      focusPoints: [
        {
          selector: "#results .mt-td--best",
          label: "Cells highlighted like this mark the best score in that column.",
        },
      ],
      actionPoint: {
        selector: '#results-toggles button[data-metric="inverse"]',
        label: "Switch to Inverse Design — this is where the tier asymmetry really shows.",
        action: { kind: "click" },
      },
    },
    {
      id: "robustness",
      title: "Robustness & Ablation",
      body: "Drag the slider below to simulate progressively deleting knowledge-graph edges and watch how ARIA absorbs the damage compared to a naive KG baseline.",
      actionPoint: {
        selector: "#robustness-slider",
        label: "Drag this to delete graph edges and watch ARIA adapt versus a naive KG baseline.",
        action: { kind: "click" },
      },
    },
    {
      id: "trace-audit",
      title: "Causal Trace Audit",
      body: "Every ARIA answer ships with an auditable, step-by-step causal trace. Walk through the example below to see how a result can be verified end to end.",
      focusPoints: [
        {
          selector: '.trace-step[data-step="3"] .completeness-bar',
          label: "The causal-completeness check that gates whether evidence is trustworthy enough to answer from.",
        },
      ],
      actionPoint: {
        selector: '.trace-step[data-step="4"] details.detail-toggle summary',
        label: "Expand to see the cited evidence behind this step.",
        action: { kind: "open-details" },
      },
    },
  ];

  // ════════════════════════════════════════════════════════════════
  // CONSTANTS — tunable from one place
  // ════════════════════════════════════════════════════════════════
  const CONSTANTS = {
    // Per-element play cadence (ms). Total ≈1000ms with an action.
    PLAY_SPRING_IN_MS: 360,
    PLAY_PRE_ACTION_MS: 100,
    PLAY_POST_ACTION_MS: 360,
    PLAY_NEXT_GAP_MS: 180,
    // Manual reveal animation
    REVEAL_SPRING_MS: 420,
    MASK_HOLE_BLOOM_MS: 280,
    CALLOUT_SPRING_MS: 320,
    // Z-indices (scrim < canvas < mask < callout < panel)
    Z_SCRIM: 400,
    Z_HIGHLIGHT: 500,
    Z_FOCUS: 450,
    Z_ACTION: 480,
    Z_MASK: 460,
    Z_CALLOUT: 470,
    Z_CONNECTOR: 460,
    Z_PANEL: 2000,
    // Easing
    SPRING: "cubic-bezier(0.34, 1.56, 0.64, 1)",
    SMOOTH: "cubic-bezier(0.22, 0.61, 0.36, 1)",
  };

  // ════════════════════════════════════════════════════════════════
  // UTILITIES
  // ════════════════════════════════════════════════════════════════
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
        new MouseEvent("click", {
          bubbles: true,
          cancelable: true,
          view: window,
        })
      );
    },
    openDetails(summaryEl) {
      if (!summaryEl) return;
      const details = summaryEl.closest("details");
      if (!details) return;
      if (!details.open) {
        details.open = true;
        // Some pages listen for the 'toggle' event to re-render.
        details.dispatchEvent(new Event("toggle"));
      }
    },
    dispatchChange(el) {
      if (!el) return;
      el.dispatchEvent(
        new Event("change", { bubbles: true, cancelable: true })
      );
    },
  };

  // ════════════════════════════════════════════════════════════════
  // RENDERER: canvas frame
  // Rounded outline + chrome that hugs a section. Sits ABOVE the
  // section's content so the section is fully visible inside, but
  // BELOW the mask. The first frame of each section shows ONLY the
  // canvas, with no mask.
  // ════════════════════════════════════════════════════════════════
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
        "Tour mode · Step " +
        meta.stepNumber +
        " of " +
        meta.totalSteps +
        " · " +
        meta.sectionTitle;
    }

    function setSubStep(done, total) {
      strip.innerHTML = "";
      for (let i = 0; i < total; i++) {
        const seg = document.createElement("span");
        seg.className = "tour-canvas__seg" + (i < done ? " is-done" : "");
        strip.appendChild(seg);
      }
    }

    function destroy() {
      root.remove();
    }

    render();
    return { root, render, setSubStep, destroy };
  }

  // ════════════════════════════════════════════════════════════════
  // RENDERER: mask
  // A single SVG that covers the section, draws a dark glass layer,
  // and punches rounded-rect holes through it for every revealed
  // element. Holes only ever grow (reveals are accumulating).
  // ════════════════════════════════════════════════════════════════
  function createMask(sectionEl) {
    const root = document.createElementNS("http://www.w3.org/2000/svg", "svg");
    root.setAttribute("class", "tour-mask-svg");
    root.setAttribute("aria-hidden", "true");
    sectionEl.appendChild(root);

    // Defs: a single mask whose white shapes become "holes".
    const defs = document.createElementNS("http://www.w3.org/2000/svg", "defs");
    const mask = document.createElementNS("http://www.w3.org/2000/svg", "mask");
    mask.setAttribute("id", "tour-mask-cutout");
    // Mask starts fully BLACK (= nothing visible through the mask).
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

    function render() {
      const sRect = sectionEl.getBoundingClientRect();
      root.setAttribute("viewBox", "0 0 " + sRect.width + " " + sRect.height);
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
      mask.querySelectorAll("rect.hole").forEach(function (n) {
        n.remove();
      });
      const sRect = sectionEl.getBoundingClientRect();
      const reduced = utils.reducedMotion();
      els.forEach(function (el, i) {
        const r = el.getBoundingClientRect();
        // Position relative to the section's top-left.
        const x = r.left - sRect.left - 6;
        const y = r.top - sRect.top - 6;
        const w = r.width + 12;
        const h = r.height + 12;
        const hole = document.createElementNS(
          "http://www.w3.org/2000/svg",
          "rect"
        );
        hole.setAttribute("class", "hole");
        hole.setAttribute("x", x);
        hole.setAttribute("y", y);
        hole.setAttribute("width", w);
        hole.setAttribute("height", h);
        // Animate rx/ry from 4 → 12 for the "bloom" on the newest hole.
        const isNewest = i === els.length - 1;
        if (isNewest && !reduced) {
          hole.setAttribute("rx", 4);
          hole.setAttribute("ry", 4);
          hole.classList.add("hole--blooming");
        } else {
          hole.setAttribute("rx", 12);
          hole.setAttribute("ry", 12);
        }
        hole.setAttribute("fill", "white");
        mask.appendChild(hole);
      });
    }

    function destroy() {
      root.remove();
    }

    render();
    return { root, render, setRevealed, destroy };
  }

  // ════════════════════════════════════════════════════════════════
  // RENDERER: callout
  // Small glass bubble that flows in next to its target. No SVG line —
  // the proximity is enough since the target is lit and the section
  // is dimmed.
  // ════════════════════════════════════════════════════════════════
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
      const goesLeft =
        tRect.left + tRect.width / 2 > window.innerWidth / 2;
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

  // ════════════════════════════════════════════════════════════════
  // RENDERER: panel
  // Bottom-right control panel. The primary slot morphs based on state.
  // ════════════════════════════════════════════════════════════════
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
        back.addEventListener("click", function () {
          state.onBack && state.onBack();
        });
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
        primary.addEventListener("click", function () {
          state.onPause && state.onPause();
        });
      } else if (state.isPaused) {
        primary.textContent = "▶ Resume";
        primary.addEventListener("click", function () {
          state.onResume && state.onResume();
        });
      } else {
        primary.textContent = "Next ▸";
        primary.addEventListener("click", function () {
          state.onNext && state.onNext();
        });
      }
      controls.appendChild(primary);

      // "Do it for me" — secondary when not primary and not at end.
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
        doIt.addEventListener("click", function () {
          state.onDoIt && state.onDoIt();
        });
        controls.appendChild(doIt);
      }

      const end = document.createElement("button");
      end.type = "button";
      end.className = "tour-btn tour-btn--ghost";
      end.textContent = "End";
      end.addEventListener("click", function () {
        state.onEnd && state.onEnd();
      });
      controls.appendChild(end);
    }

    function setState(state) {
      render(state);
    }

    render(initial);
    return { root, setState, destroy: function () { root.remove(); } };
  }

  // ════════════════════════════════════════════════════════════════
  // ORCHESTRATOR: SiteTour
  // Owns state, lifecycle, sub-step index, play loop, keyboard.
  // ════════════════════════════════════════════════════════════════
  class SiteTour {
    constructor(stops) {
      this.stops = stops.filter(function (stop) {
        return document.getElementById(stop.id);
      });
      this._index = -1;
      this._subIndex = -1; // -1 = first-frame canvas (nothing revealed yet)
      this._revealed = []; // elements revealed in the current section
      this._mode = "idle"; // 'idle' | 'playing' | 'paused'
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
      window.addEventListener("scroll", this._onViewportChange, {
        passive: true,
      });
      window.addEventListener("resize", this._onViewportChange);
      this._goto(0, -1);
    }

    end() {
      if (!this._active) return;
      this._cancelPlay();
      const cur = this.stops[this._index];
      if (cur && typeof cur.onLeave === "function") {
        try {
          cur.onLeave(document.getElementById(cur.id));
        } catch (e) {}
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
          const prev = this.stops[this._index - 1];
          this._goto(this._index - 1, this._subStepTotal(prev) - 1);
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
      if (total > 0 && this._subIndex >= total - 1) {
        this._cancelPlay();
        this._goto(this._index, -1);
      }
      this._mode = "playing";
      this._refreshPanel();
      let i = this._subIndex + 1;
      let cancelled = false;
      this._playCancel = function () {
        cancelled = true;
      };

      const self = this;
      const step = function () {
        if (cancelled || !self._active) return;
        if (i >= total) {
          self._mode = "idle";
          self._playCancel = null;
          self._refreshPanel();
          return;
        }
        self._goto(self._index, i);
        const el = self._currentSubStepEl();
        const pt = self._currentSubStepPoint();
        const fire = function () {
          if (pt && pt.action) {
            if (pt.action.kind === "click") utils.dispatchClick(el);
            else if (pt.action.kind === "open-details")
              utils.openDetails(el);
            else if (pt.action.kind === "change") utils.dispatchChange(el);
          }
        };
        const next = function () {
          if (cancelled || !self._active) return;
          if (self._mode === "paused") {
            // Pause: poll lightly until resumed.
            const wait = setInterval(function () {
              if (cancelled || !self._active) {
                clearInterval(wait);
                return;
              }
              if (self._mode === "playing") {
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
        window.setTimeout(
          fire,
          CONSTANTS.PLAY_SPRING_IN_MS + CONSTANTS.PLAY_PRE_ACTION_MS
        );
        window.setTimeout(
          next,
          CONSTANTS.PLAY_SPRING_IN_MS +
            CONSTANTS.PLAY_PRE_ACTION_MS +
            CONSTANTS.PLAY_POST_ACTION_MS
        );
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

    isPlaying() {
      return this._mode === "playing";
    }

    // ── Internals ──

    _subStepTotal(stop) {
      if (!stop) return 0;
      const fps = stop.focusPoints ? stop.focusPoints.length : 0;
      return fps + (stop.actionPoint ? 1 : 0);
    }

    _subStepPoint(stop, subIndex) {
      if (!stop) return null;
      const fps = stop.focusPoints || [];
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
      if (this._canvas) {
        this._canvas.destroy();
        this._canvas = null;
      }
      if (this._mask) {
        this._mask.destroy();
        this._mask = null;
      }
      if (this._callout) {
        this._callout.destroy();
        this._callout = null;
      }
      if (this._panel) {
        this._panel.destroy();
        this._panel = null;
      }
    }

    _goto(index, subIndex) {
      const prev = this.stops[this._index];

      // Section transition
      if (prev && prev !== this.stops[index]) {
        if (typeof prev.onLeave === "function") {
          try {
            prev.onLeave(document.getElementById(prev.id));
          } catch (e) {}
        }
        this._destroyRenderers();
        this._revealed = [];
      } else if (prev === this.stops[index] && subIndex < this._subIndex) {
        // Going back within a section — re-reveal up to subIndex.
        this._revealed = this._revealed.slice(0, subIndex + 1);
        if (this._callout) {
          this._callout.destroy();
          this._callout = null;
        }
      } else if (prev === this.stops[index] && subIndex > this._subIndex) {
        // Going forward within a section — append the new element.
        const pt = this._subStepPoint(this.stops[index], subIndex);
        if (pt) {
          const el = utils.getEl(pt.selector);
          if (el) this._revealed.push(el);
        }
      }

      this._index = index;
      this._subIndex = subIndex;
      const stop = this.stops[index];
      const sectionEl = document.getElementById(stop.id);
      if (!sectionEl) {
        this.next();
        return;
      }

      // Fire onEnter for the new stop (only when we just changed stop).
      if (prev !== stop) {
        if (typeof stop.onEnter === "function") {
          try {
            stop.onEnter(sectionEl);
          } catch (e) {}
        }
      }

      // Scroll into view (smooth, unless reduced motion).
      const reduced = utils.reducedMotion();
      sectionEl.scrollIntoView({
        behavior: reduced ? "auto" : "smooth",
        block: "center",
      });

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
      // subIndex === -1 means "first frame of this section".
      if (subIndex < 0) {
        this._revealed = [];
        this._mask.setRevealed([]);
        this._canvas.setSubStep(0, this._subStepTotal(stop));
        if (this._callout) {
          this._callout.destroy();
          this._callout = null;
        }
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
      this._canvas.setSubStep(
        this._revealed.length,
        this._subStepTotal(stop)
      );
      if (this._callout) {
        this._callout.destroy();
        this._callout = null;
      }
      const curPt = this._subStepPoint(stop, subIndex);
      const curEl = curPt ? utils.getEl(curPt.selector) : null;
      if (curPt && curEl) {
        this._callout = createCallout(curEl, { text: curPt.label });
        if (utils.reducedMotion()) {
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
      const self = this;
      this._rafScheduled = true;
      window.requestAnimationFrame(function () {
        self._rafScheduled = false;
        const stop = self.stops[self._index];
        const sectionEl = stop ? document.getElementById(stop.id) : null;
        if (!sectionEl) return;
        if (self._canvas) self._canvas.render();
        if (self._mask) self._mask.setRevealed(self._revealed);
        if (self._callout) self._callout.reposition();
      });
    }

    _onKeydown(e) {
      if (!this._active) return;
      if (e.key === "Escape") {
        this.end();
        return;
      }
      if (e.key === "ArrowRight" || e.key === " ") {
        if (this._mode === "playing") this.pause();
        else this.next();
        if (e.preventDefault) e.preventDefault();
      } else if (e.key === "ArrowLeft") {
        this.back();
        if (e.preventDefault) e.preventDefault();
      }
    }

    _injectStyles() {
      if (document.getElementById("tour-styles")) return;
      const style = document.createElement("style");
      style.id = "tour-styles";
      style.textContent = `
/* ── Tour canvas (first frame of each section) ── */
.tour-canvas {
  position: fixed;
  z-index: 499;
  pointer-events: none;
  border-radius: 22px;
  outline: 1.5px solid rgba(104, 172, 229, 0.35);
  outline-offset: 0;
  transition: outline-color 0.2s cubic-bezier(0.22, 0.61, 0.36, 1);
  animation: tour-canvas-in 0.4s cubic-bezier(0.22, 0.61, 0.36, 1) both;
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
  white-space: nowrap;
  max-width: calc(100% - 32px);
  overflow: hidden;
  text-overflow: ellipsis;
}
.tour-canvas__strip {
  position: absolute;
  top: -2px;
  left: 50%;
  transform: translateX(-50%);
  display: flex;
  gap: 4px;
  padding: 3px 8px;
  background: rgba(6, 10, 22, 0.85);
  border-radius: 9999px;
  pointer-events: auto;
}
.tour-canvas__seg {
  width: 14px;
  height: 3px;
  border-radius: 2px;
  background: rgba(255, 255, 255, 0.18);
  transition: background 0.3s cubic-bezier(0.22, 0.61, 0.36, 1);
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
  transition: background 0.15s cubic-bezier(0.22, 0.61, 0.36, 1),
              transform 0.15s cubic-bezier(0.22, 0.61, 0.36, 1);
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
  z-index: 460;
  pointer-events: none;
  backdrop-filter: blur(2px);
  -webkit-backdrop-filter: blur(2px);
}
.tour-mask-svg rect.hole--blooming {
  animation: tour-hole-bloom 280ms cubic-bezier(0.34, 1.56, 0.64, 1) both;
}
@keyframes tour-hole-bloom {
  from { rx: 4; ry: 4; }
  to   { rx: 12; ry: 12; }
}

/* ── Tour callout ── */
.tour-callout {
  position: fixed;
  z-index: 470;
  width: min(220px, calc(50vw - 48px));
  padding: 10px 14px;
  pointer-events: auto;
  animation: tour-callout-in-right 320ms cubic-bezier(0.34, 1.56, 0.64, 1) both;
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
  z-index: 2000;
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
  transition: background 0.3s cubic-bezier(0.22, 0.61, 0.36, 1),
              transform 0.3s cubic-bezier(0.34, 1.56, 0.64, 1);
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
  transition: transform 0.15s cubic-bezier(0.22, 0.61, 0.36, 1),
              background 0.15s cubic-bezier(0.22, 0.61, 0.36, 1),
              box-shadow 0.2s cubic-bezier(0.22, 0.61, 0.36, 1);
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
  0%, 100% { transform: scale(1);    box-shadow: 0 0 0 0 rgba(104, 172, 229, 0.28); }
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
  .tour-canvas__pill {
    left: 12px;
    right: 12px;
    max-width: calc(100% - 24px);
    font-size: 10.5px;
  }
  .tour-canvas__end {
    right: 12px;
  }
}
      `;
      document.head.appendChild(style);
    }
  }

  // ════════════════════════════════════════════════════════════════
  // BOOTSTRAP
  // ════════════════════════════════════════════════════════════════
  function init() {
    const tour = new SiteTour(STOPS);
    const button = document.getElementById("tour-start-btn");
    if (button) {
      button.addEventListener("click", function (event) {
        event.preventDefault();
        tour.start();
      });
    }
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }
})();
