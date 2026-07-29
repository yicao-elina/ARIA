/**
 * tour.js — Guided, operational walkthrough of the ARIA site.
 *
 * v2 (2026-07-29, revised): "all-holes-at-once" tour.
 *   - Section enters with the mask and holes immediately visible:
 *     each clickable element in the section is revealed together
 *     with an SVG-mask cutout, a dashed-leader label chip
 *     (1, 2, 3...), and a soft breathing ring.
 *   - User clicks each hole (or hits "Do it for me" to automate the
 *     same sequence). Clicking fires the element's action
 *     (open-details / click / change) and the hole settles.
 *   - When all holes are clicked, the mask fades out, the section
 *     returns to fully clear for 3s, then the panel "Next" breathes
 *     to prompt the user to advance.
 *
 * Self-contained page chrome. No dependencies. Self-initializes on
 * DOMContentLoaded (guarded for the case the script executes after
 * the event already fired, since it is loaded with `defer`).
 */
(function () {
  "use strict";

  // ════════════════════════════════════════════════════════════════
  // DATA: stops
  // Each stop is a section. The section's `focusPoints` (plus the
  // `actionPoint`, treated as the last hole) are the clickable
  // elements that get revealed together as soon as the section
  // is entered.
  // ════════════════════════════════════════════════════════════════
  const STOPS = [
    {
      id: "problem",
      title: "The Problem: Contextual Tunneling",
      body: "Compare a baseline LLM against a naive KG+LLM system below — the naive system over-anchors on partial evidence. Try the demo to see the failure mode ARIA is built to prevent.",
      focusPoints: [
        {
          selector: "#problem .tunneling-panel--naive-kg .tunneling-segment--error",
          label: "Contextual tunneling: a plausible-sounding claim built by over-anchoring on partial KG evidence.",
        },
        {
          selector: "#problem .tunneling-panel--baseline",
          label: "The baseline LLM avoids the trap — but has no causal grounding at all.",
        },
      ],
      actionPoint: {
        selector: "#problem .tunneling-example-btn:nth-of-type(2)",
        label: "Try Example 2 to see the same failure mode on a different query.",
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
      body: "This is ARIA's core mechanism. Try clicking example pills and “Route Query” to watch a query get routed through Tier 1, 2, or 3 based on causal completeness.",
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
      body: "Each tier has a worked example. Click any of the highlighted summaries to expand the trace for that tier.",
      focusPoints: [
        {
          selector: "#tier-deep-dive .tier-1-detail summary",
          label: "Already open — see the full causal trace from processing to property below.",
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
        label: "Expand to see ARIA validate physical constraints before transferring MoS₂'s mechanism to MoSe₂.",
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
        selector: "#fig-results",
        label: "This is where the tier asymmetry really shows — forward prediction vs. inverse design.",
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
    // Per-section timing (ms)
    CLEAR_BETWEEN_SECTIONS_MS: 3000, // fully clear after all holes clicked
    MASK_FADE_IN_MS: 380,
    MASK_FADE_OUT_MS: 400,
    CHIP_ENTRANCE_MS: 320,
    BREATH_PERIOD_MS: 2000,
    NEXT_BREATH_PERIOD_MS: 2400,
    // Auto-play pacing
    AUTO_PLAY_GAP_MS: 1000,
    // Z-indices
    Z_CANVAS: 499,
    Z_MASK: 460,
    Z_LABEL: 470,
    Z_LABEL_CONNECTOR: 461,
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
    getAllEl(selector) {
      try {
        return Array.from(document.querySelectorAll(selector));
      } catch (e) {
        return [];
      }
    },
    reducedMotion() {
      return (
        window.matchMedia &&
        window.matchMedia("(prefers-reduced-motion: reduce)").matches
      );
    },
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
        details.dispatchEvent(new Event("toggle"));
      }
    },
    dispatchChange(el) {
      if (!el) return;
      el.dispatchEvent(
        new Event("change", { bubbles: true, cancelable: true })
      );
    },
    wait(ms) {
      return new Promise((resolve) => window.setTimeout(resolve, ms));
    },
  };

  // ════════════════════════════════════════════════════════════════
  // RENDERER: canvas frame
  // A thin rounded outline + corner pill. Shows "Step N of M · title"
  // and a one-line hint ("Click the highlighted elements"). No
  // sub-step strip in this revision.
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

    const hint = document.createElement("div");
    hint.className = "tour-canvas__hint";
    root.appendChild(hint);

    const endBtn = document.createElement("button");
    endBtn.type = "button";
    endBtn.className = "tour-canvas__end";
    endBtn.setAttribute("aria-label", "End tour");
    endBtn.textContent = "End Tour ✕";
    endBtn.addEventListener("click", function () {
      meta.onEnd && meta.onEnd();
    });
    root.appendChild(endBtn);

    function render() {
      const rect = sectionEl.getBoundingClientRect();
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

    function setHint(text) {
      if (text) {
        hint.textContent = text;
        hint.classList.add("is-visible");
      } else {
        hint.classList.remove("is-visible");
      }
    }

    function destroy() {
      root.remove();
    }

    render();
    return { root, render, setHint, destroy };
  }

  // ════════════════════════════════════════════════════════════════
  // RENDERER: mask (SVG cutouts)
  // A single SVG that covers the section. One dark glass layer with
  // rounded-rect holes punched through it. Holes have a "breathing"
  // pulse via a CSS animation.
  // ════════════════════════════════════════════════════════════════
  function createMask(sectionEl) {
    const root = document.createElementNS("http://www.w3.org/2000/svg", "svg");
    root.setAttribute("class", "tour-mask-svg");
    root.setAttribute("aria-hidden", "true");
    sectionEl.appendChild(root);

    const defs = document.createElementNS("http://www.w3.org/2000/svg", "defs");
    const mask = document.createElementNS("http://www.w3.org/2000/svg", "mask");
    mask.setAttribute("id", "tour-mask-cutout");
    // SVG mask convention: WHITE = visible (dark layer shows), BLACK = hidden (hole).
    // Background = white (everywhere dimmed); holes are punched BLACK so the
    // section content shows through them clearly.
    const bg = document.createElementNS("http://www.w3.org/2000/svg", "rect");
    bg.setAttribute("x", "0");
    bg.setAttribute("y", "0");
    bg.setAttribute("width", "100%");
    bg.setAttribute("height", "100%");
    bg.setAttribute("fill", "white");
    mask.appendChild(bg);
    defs.appendChild(mask);
    root.appendChild(defs);

    const layer = document.createElementNS("http://www.w3.org/2000/svg", "rect");
    layer.setAttribute("class", "tour-mask-layer");
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

    // holes: [{ el, label, text, action, rect, hole, settled }]
    const holes = [];
    let fadedOut = false;

    function setHoles(newHoles) {
      // Clear existing
      mask.querySelectorAll("rect.hole").forEach((n) => n.remove());
      holes.length = 0;
      const sRect = sectionEl.getBoundingClientRect();
      const reduced = utils.reducedMotion();
      newHoles.forEach((h, i) => {
        const r = h.el.getBoundingClientRect();
        const x = r.left - sRect.left - 8;
        const y = r.top - sRect.top - 8;
        const w = r.width + 16;
        const hgt = r.height + 16;
        const hole = document.createElementNS("http://www.w3.org/2000/svg", "rect");
        hole.setAttribute("class", "hole");
        hole.setAttribute("x", x);
        hole.setAttribute("y", y);
        hole.setAttribute("width", w);
        hole.setAttribute("height", hgt);
        if (reduced) {
          hole.setAttribute("rx", 12);
          hole.setAttribute("ry", 12);
        } else {
          hole.setAttribute("rx", 4);
          hole.setAttribute("ry", 4);
          hole.classList.add("hole--blooming");
        }
        hole.setAttribute("fill", "black");
        mask.appendChild(hole);
        holes.push({
          el: h.el,
          label: h.label,
          text: h.text,
          action: h.action,
          rect: { x, y, w, h: hgt },
          hole,
          settled: false,
        });
      });
    }

    function updateHoleRects() {
      const sRect = sectionEl.getBoundingClientRect();
      holes.forEach((h) => {
        if (!h.el.isConnected) return;
        const r = h.el.getBoundingClientRect();
        h.rect = {
          x: r.left - sRect.left - 8,
          y: r.top - sRect.top - 8,
          w: r.width + 16,
          h: r.height + 16,
        };
        h.hole.setAttribute("x", h.rect.x);
        h.hole.setAttribute("y", h.rect.y);
        h.hole.setAttribute("width", h.rect.w);
        h.hole.setAttribute("height", h.rect.h);
      });
    }

    function settleHole(el) {
      const h = holes.find((x) => x.el === el);
      if (!h || h.settled) return;
      h.settled = true;
      h.hole.classList.remove("hole--blooming");
      h.hole.classList.add("hole--settled");
    }

    function fadeIn() {
      fadedOut = false;
      root.classList.remove("is-fading-out");
      root.classList.add("is-fading-in");
    }

    function fadeOut() {
      fadedOut = true;
      root.classList.remove("is-fading-in");
      root.classList.add("is-fading-out");
    }

    function clear() {
      holes.length = 0;
      mask.querySelectorAll("rect.hole").forEach((n) => n.remove());
      root.classList.remove("is-fading-in", "is-fading-out");
    }

    function getHoles() {
      return holes;
    }

    function isFadedOut() {
      return fadedOut;
    }

    function destroy() {
      root.remove();
    }

    render();
    return {
      root,
      render,
      setHoles,
      updateHoleRects,
      settleHole,
      fadeIn,
      fadeOut,
      clear,
      getHoles,
      isFadedOut,
      destroy,
    };
  }

  // ════════════════════════════════════════════════════════════════
  // RENDERER: hole label
  // A persistent callout pill containing the number AND the
  // explanatory text, with a dashed SVG leader line to the hole.
  // The text is always visible at body-text size (no hover-only
  // tooltip). The pill sits above the hole by default; if there
  // is no room, it falls back to the right of the hole.
  // ════════════════════════════════════════════════════════════════
  function createHoleLabel(targetEl, label, text) {
    const root = document.createElement("div");
    root.className = "tour-hole-label";
    const chip = document.createElement("div");
    chip.className = "tour-hole-label__chip";
    chip.textContent = label;
    const callout = document.createElement("div");
    callout.className = "tour-hole-label__callout";
    callout.textContent = text || "";
    root.appendChild(callout);
    root.appendChild(chip);
    document.body.appendChild(root);

    // Dashed leader line in its own SVG so it can sit behind the chip.
    const svg = document.createElementNS("http://www.w3.org/2000/svg", "svg");
    svg.setAttribute("class", "tour-hole-label__svg");
    svg.setAttribute("aria-hidden", "true");
    const line = document.createElementNS("http://www.w3.org/2000/svg", "line");
    line.setAttribute("class", "tour-hole-label__line");
    svg.appendChild(line);
    document.body.appendChild(svg);

    function place() {
      const r = targetEl.getBoundingClientRect();
      const tRect = root.getBoundingClientRect();
      const margin = 12;
      const gap = 22;
      // Prefer to put the callout above the target; if no room,
      // put it to the right of the target.
      const wantTop = r.top - tRect.height - gap > margin;
      let left, top, x1, y1, x2, y2;
      if (wantTop) {
        // Center horizontally over the target, clamped to viewport.
        left = r.left + r.width / 2 - tRect.width / 2;
        left = Math.min(
          Math.max(left, margin),
          window.innerWidth - tRect.width - margin
        );
        top = r.top - tRect.height - gap;
        // Leader line: from callout's bottom-center down to target's top-center.
        const calloutCx = left + tRect.width / 2;
        const calloutBy = top + tRect.height;
        const tx = r.left + r.width / 2;
        const ty = r.top;
        x1 = calloutCx;
        y1 = calloutBy;
        x2 = tx;
        y2 = ty;
      } else {
        // Right of the target.
        left = r.right + gap;
        left = Math.min(
          Math.max(left, margin),
          window.innerWidth - tRect.width - margin
        );
        top = r.top + r.height / 2 - tRect.height / 2;
        top = Math.min(
          Math.max(top, margin),
          window.innerHeight - tRect.height - margin
        );
        const calloutL = left;
        const calloutCy = top + tRect.height / 2;
        const tx = r.right;
        const ty = r.top + r.height / 2;
        x1 = calloutL;
        y1 = calloutCy;
        x2 = tx;
        y2 = ty;
      }
      root.style.left = left + "px";
      root.style.top = top + "px";
      svg.setAttribute(
        "viewBox",
        "0 0 " + window.innerWidth + " " + window.innerHeight
      );
      svg.setAttribute("width", window.innerWidth);
      svg.setAttribute("height", window.innerHeight);
      svg.style.left = "0px";
      svg.style.top = "0px";
      line.setAttribute("x1", x1);
      line.setAttribute("y1", y1);
      line.setAttribute("x2", x2);
      line.setAttribute("y2", y2);
    }

    function settle() {
      root.classList.add("is-settled");
      line.classList.add("is-settled");
    }

    function destroy() {
      root.remove();
      svg.remove();
    }

    place();
    return { root, svg, line, place, settle, destroy };
  }

  // ════════════════════════════════════════════════════════════════
  // RENDERER: panel (bottom-right)
  // The primary slot morphs based on tour state.
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

    const hint = document.createElement("div");
    hint.className = "tour-panel__hint";
    root.appendChild(hint);

    const controls = document.createElement("div");
    controls.className = "tour-panel__controls";
    root.appendChild(controls);

    function render(state) {
      progress.textContent =
        "Step " + state.stepNumber + " of " + state.totalSteps;
      title.textContent = state.sectionTitle;
      if (state.hint) {
        hint.textContent = state.hint;
        hint.classList.add("is-visible");
      } else {
        hint.classList.remove("is-visible");
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
      if (state.isAutoPlaying) {
        primary.textContent = "Skip ▸▸";
        primary.classList.remove("tour-btn--breathing");
        primary.addEventListener("click", function () {
          state.onSkip && state.onSkip();
        });
      } else if (state.canAdvance) {
        primary.textContent = "Next ▸";
        primary.classList.add("tour-btn--breathing");
        primary.addEventListener("click", function () {
          state.onNext && state.onNext();
        });
      } else if (state.holesTotal > 0) {
        primary.textContent = "Do it for me ▶";
        primary.classList.add("tour-btn--breathing");
        primary.addEventListener("click", function () {
          state.onDoIt && state.onDoIt();
        });
      } else {
        // Section has no holes (e.g. PSP / robustness). Show Next.
        primary.textContent = "Next ▸";
        primary.classList.add("tour-btn--breathing");
        primary.addEventListener("click", function () {
          state.onNext && state.onNext();
        });
      }
      controls.appendChild(primary);

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
  // State machine:
  //   'idle'         — section is fully clear
  //   'revealing'    — mask fading in, holes breathing, user clicking
  //   'settling'     — all holes clicked, mask fading out
  //   'auto-playing' — "Do it for me" running
  //   'clearing'     — fully clear, waiting for user Next
  // ════════════════════════════════════════════════════════════════
  class SiteTour {
    constructor(stops) {
      this.stops = stops.filter((s) => document.getElementById(s.id));
      this._index = -1;
      this._mode = "idle";
      this._autoPlayCancel = null;
      this._timers = [];
      this._active = false;
      this._canvas = null;
      this._mask = null;
      this._panel = null;
      this._labels = []; // array of createHoleLabel instances
      this._holes = [];  // [{ el, label, text, action }]
      this._onKeydown = this._onKeydown.bind(this);
      this._onViewportChange = this._reposition.bind(this);
      this._rafScheduled = false;
      this._injectStyles();
    }

    start() {
      if (!this.stops.length || this._active) return;
      this._active = true;
      this._index = 0;
      document.addEventListener("keydown", this._onKeydown);
      window.addEventListener("scroll", this._onViewportChange, {
        passive: true,
      });
      window.addEventListener("resize", this._onViewportChange);
      this._goto(0);
    }

    end() {
      if (!this._active) return;
      this._cancelAutoPlay();
      this._clearTimers();
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

    // Panel "Next" handler. Only advances if the section is in the
    // "ready to advance" state (i.e. user has clicked all holes
    // and the post-clear beat is over).
    next() {
      if (!this._active) return;
      if (this._mode !== "clearing") {
        // Nudge: pulse the panel a bit so the user knows to wait.
        this._nudgePanel();
        return;
      }
      if (this._index >= this.stops.length - 1) {
        this.end();
        return;
      }
      this._goto(this._index + 1);
    }

    back() {
      if (!this._active) return;
      if (this._index <= 0) return;
      this._cancelAutoPlay();
      this._clearTimers();
      this._goto(this._index - 1);
    }

    doItForMe() {
      if (!this._active) return;
      if (this._mode !== "revealing") return;
      if (this._holes.length === 0) {
        // No holes — just advance the section.
        this._settleAllHoles();
        return;
      }
      this._mode = "auto-playing";
      this._refreshPanel();
      const self = this;
      let i = 0;
      let cancelled = false;
      this._autoPlayCancel = () => {
        cancelled = true;
      };
      const step = () => {
        if (cancelled || !self._active) return;
        if (i >= self._holes.length) {
          self._autoPlayCancel = null;
          self._settleAllHoles();
          return;
        }
        const h = self._holes[i];
        self._fireHole(h);
        i += 1;
        window.setTimeout(step, CONSTANTS.AUTO_PLAY_GAP_MS);
      };
      window.setTimeout(step, 60);
    }

    skipAutoPlay() {
      this._cancelAutoPlay();
      this._settleAllHoles();
    }

    isActive() {
      return this._active;
    }

    // ── Internals ──

    _cancelAutoPlay() {
      if (this._autoPlayCancel) {
        this._autoPlayCancel();
        this._autoPlayCancel = null;
      }
      if (this._mode === "auto-playing") this._mode = "revealing";
    }

    _clearTimers() {
      this._timers.forEach((t) => window.clearTimeout(t));
      this._timers = [];
    }

    _addTimer(t) {
      this._timers.push(t);
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
      if (this._panel) {
        this._panel.destroy();
        this._panel = null;
      }
      this._labels.forEach((l) => l.destroy());
      this._labels = [];
      this._holes = [];
    }

    _goto(index) {
      this._cancelAutoPlay();
      this._clearTimers();
      const prev = this.stops[this._index];
      if (prev && typeof prev.onLeave === "function") {
        try {
          prev.onLeave(document.getElementById(prev.id));
        } catch (e) {}
      }
      this._destroyRenderers();
      this._index = index;
      const stop = this.stops[index];
      const sectionEl = document.getElementById(stop.id);
      if (!sectionEl) {
        // Skip missing sections.
        if (index < this.stops.length - 1) this._goto(index + 1);
        else this.end();
        return;
      }

      if (typeof stop.onEnter === "function") {
        try {
          stop.onEnter(sectionEl);
        } catch (e) {}
      }

      const reduced = utils.reducedMotion();
      sectionEl.scrollIntoView({
        behavior: reduced ? "auto" : "smooth",
        block: "center",
      });

      // Build the canvas frame, mask, and panel up front so the
      // "clear" beat already has its chrome in place.
      this._canvas = createCanvasFrame(sectionEl, {
        stepNumber: this._index + 1,
        totalSteps: this.stops.length,
        sectionTitle: stop.title,
        onEnd: () => this.end(),
      });
      this._mask = createMask(sectionEl);
      // Mask starts visible (will fade in via the is-fading-in
      // transition applied in _revealAllHoles()).

      // Collect holes.
      const holes = [];
      const fps = stop.focusPoints || [];
      fps.forEach((p) => {
        const el = utils.getEl(p.selector);
        if (el) {
          holes.push({
            el,
            label: "",
            text: p.label || "",
            action: p.action || null,
          });
        }
      });
      if (stop.actionPoint) {
        const el = utils.getEl(stop.actionPoint.selector);
        if (el) {
          holes.push({
            el,
            label: "",
            text: stop.actionPoint.label || "",
            action: stop.actionPoint.action || null,
          });
        }
      }
      // Number holes 1, 2, 3...
      holes.forEach((h, i) => {
        h.label = String(i + 1);
      });
      this._holes = holes;
      const useLetters = stop.labels === "letters";
      if (useLetters) {
        this._holes.forEach((h, i) => {
          h.label = String.fromCharCode("a".charCodeAt(0) + i);
        });
      }

      this._panel = createPanel(this._panelState(stop));
      this._mode = "revealing";
      this._refreshPanel();

      // Reveal holes and fade in the mask immediately. Use a single
      // rAF to let the browser paint the freshly-mounted canvas before
      // the fade-in transition begins.
      window.requestAnimationFrame(() => {
        this._revealAllHoles();
      });
    }

    _setHint(text) {
      if (this._canvas) this._canvas.setHint(text);
    }

    _setHintOnStop(stop, phase) {
      // phase: 'clear' | 'revealing' | 'clearing' | 'ready'
      if (phase === "clear") {
        this._setHint("");
      } else if (phase === "revealing") {
        if (this._holes.length > 0) {
          this._setHint("Click the highlighted elements");
        } else {
          this._setHint("");
        }
      } else if (phase === "clearing") {
        this._setHint("");
      }
    }

    _revealAllHoles() {
      if (!this._active) return;
      this._mode = "revealing";
      this._mask.setHoles(this._holes);
      this._mask.fadeIn();
      this._setHintOnStop(this.stops[this._index], "revealing");
      // Build labels.
      this._holes.forEach((h) => {
        const label = createHoleLabel(h.el, h.label, h.text);
        // Click on the label's chip also fires the action — same as
        // clicking the hole itself.
        label.root.addEventListener("click", (e) => {
          e.preventDefault();
          e.stopPropagation();
          this._fireHole(h);
        });
        this._labels.push(label);
      });
      this._refreshPanel();
      this._reposition();
    }

    _fireHole(h) {
      // Fire the action. The element's own click / open / change
      // handlers will mutate the DOM (e.g. expand <details>); the
      // layout will shift, so we re-measure on the next frame.
      if (h.action) {
        if (h.action.kind === "click") utils.dispatchClick(h.el);
        else if (h.action.kind === "open-details") utils.openDetails(h.el);
        else if (h.action.kind === "change") utils.dispatchChange(h.el);
      } else {
        // No action: still "settle" the hole so the user gets
        // feedback that they did the right thing.
        utils.dispatchClick(h.el);
      }
      this._mask.settleHole(h.el);
      const lab = this._labels.find((l) => l && l.root.dataset && l.root.dataset.labelKey === h.label);
      // Use a simpler lookup: match by text.
      this._labels.forEach((l) => {
        if (!l || l.root.classList.contains("is-settled")) return;
        if (l.root.querySelector(".tour-hole-label__chip").textContent === h.label) {
          l.settle();
        }
      });
      this._refreshPanel();
      // After layout shifts, re-measure the mask and labels.
      window.requestAnimationFrame(() => this._reposition());

      // If all holes settled, transition to clearing.
      if (this._allHolesSettled()) {
        this._settleAllHoles();
      }
    }

    _allHolesSettled() {
      if (this._holes.length === 0) return false;
      return this._labels.every((l) => l.root.classList.contains("is-settled"));
    }

    _settleAllHoles() {
      if (this._mode === "clearing" || this._mode === "idle") return;
      this._mode = "clearing";
      this._mask.fadeOut();
      this._setHintOnStop(this.stops[this._index], "clearing");
      this._refreshPanel();

      // After the clear beat, mark as "ready to advance" so the
      // panel Next button starts breathing.
      this._clearTimers();
      this._addTimer(
        window.setTimeout(
          () => this._markReady(),
          CONSTANTS.CLEAR_BETWEEN_SECTIONS_MS
        )
      );
    }

    _markReady() {
      if (this._mode !== "clearing") return;
      this._mode = "clearing"; // still clearing visually; the panel
      // shows Next-breathing because canAdvance is true.
      this._refreshPanel();
    }

    _panelState(stop) {
      const holesTotal = this._holes.length;
      const holesDone = this._labels.filter((l) =>
        l.root.classList.contains("is-settled")
      ).length;
      const canAdvance =
        this._mode === "clearing" && holesTotal === holesDone;
      let hint = "";
      if (this._mode === "clearing" && holesTotal > 0) {
        hint = "Section complete — Next to continue";
      } else if (this._mode === "revealing" && holesTotal > 0) {
        hint = "Click the highlighted elements";
      }
      return {
        stepNumber: this._index + 1,
        totalSteps: this.stops.length,
        sectionTitle: stop.title,
        holesTotal,
        holesDone,
        canAdvance,
        canBack: this._index > 0,
        isAutoPlaying: this._mode === "auto-playing",
        hint,
        onBack: () => this.back(),
        onDoIt: () => this.doItForMe(),
        onSkip: () => this.skipAutoPlay(),
        onNext: () => this.next(),
        onEnd: () => this.end(),
      };
    }

    _refreshPanel() {
      if (!this._panel) return;
      this._panel.setState(this._panelState(this.stops[this._index]));
    }

    _nudgePanel() {
      if (!this._panel) return;
      const root = this._panel.root;
      root.classList.remove("is-nudge");
      // force reflow
      void root.offsetWidth;
      root.classList.add("is-nudge");
    }

    _reposition() {
      if (this._rafScheduled) return;
      const self = this;
      this._rafScheduled = true;
      window.requestAnimationFrame(function () {
        self._rafScheduled = false;
        if (!self._active) return;
        if (self._canvas) self._canvas.render();
        if (self._mask) self._mask.updateHoleRects();
        self._labels.forEach((l) => l.place());
      });
    }

    _onKeydown(e) {
      if (!this._active) return;
      if (e.key === "Escape") {
        this.end();
        return;
      }
      if (e.key === "ArrowRight" || e.key === " ") {
        if (this._mode === "auto-playing") this.skipAutoPlay();
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
  z-index: ${CONSTANTS.Z_CANVAS};
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
  white-space: nowrap;
  max-width: calc(100% - 200px);
  overflow: hidden;
  text-overflow: ellipsis;
}
.tour-canvas__hint {
  position: absolute;
  top: 14px;
  right: 16px;
  padding: 4px 10px;
  border-radius: 9999px;
  background: rgba(6, 10, 22, 0.78);
  color: #fff;
  font-size: 11.5px;
  font-weight: 500;
  pointer-events: none;
  opacity: 0;
  transform: translateY(-4px);
  transition: opacity 0.3s ${CONSTANTS.SMOOTH},
              transform 0.3s ${CONSTANTS.SMOOTH};
}
.tour-canvas__hint.is-visible {
  opacity: 1;
  transform: translateY(0);
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
  transition: background 0.15s ${CONSTANTS.SMOOTH},
              transform 0.15s ${CONSTANTS.SMOOTH};
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
  /* No backdrop-filter here: it would blur the holes (lit regions) too. */
  opacity: 0;
  transition: opacity ${CONSTANTS.MASK_FADE_IN_MS}ms ${CONSTANTS.SMOOTH};
}
.tour-mask-svg.is-fading-in { opacity: 1; }
.tour-mask-svg.is-fading-out {
  opacity: 0;
  transition: opacity ${CONSTANTS.MASK_FADE_OUT_MS}ms ${CONSTANTS.SMOOTH};
}
.tour-mask-svg rect.hole--blooming {
  animation: tour-hole-bloom 320ms ${CONSTANTS.SPRING} both,
             tour-hole-breath ${CONSTANTS.BREATH_PERIOD_MS}ms ease-in-out infinite 320ms;
}
.tour-mask-svg rect.hole--settled {
  animation: none;
}
@keyframes tour-hole-bloom {
  from { rx: 4; ry: 4; }
  to   { rx: 14; ry: 14; }
}
@keyframes tour-hole-breath {
  0%, 100% { rx: 14; ry: 14; }
  50%      { rx: 16; ry: 16; }
}

/* The mask LAYER's mask cutouts (the white rects in the mask)
   are themselves the "breathing ring" — the rect's stroke could
   grow, but since the mask only contributes the white-fill shape,
   the breath is a faint inset ring rendered as the rect's
   box-shadow on the section element behind the mask. */

/* ── Tour hole label (callout pill with chip + dashed leader line) ── */
.tour-hole-label {
  position: fixed;
  z-index: ${CONSTANTS.Z_LABEL};
  pointer-events: none;
  display: flex;
  align-items: center;
  gap: 8px;
  max-width: min(420px, calc(100vw - 32px));
  animation: tour-chip-in ${CONSTANTS.CHIP_ENTRANCE_MS}ms ${CONSTANTS.SPRING} both;
}
/* The callout is the persistent text label — always visible. */
.tour-hole-label__callout {
  font-family: var(--font-display, inherit);
  font-size: 16px;
  font-weight: 500;
  line-height: 1.4;
  color: var(--apple-text-primary, #002D72);
  background: rgba(255, 255, 255, 0.96);
  padding: 7px 12px;
  border-radius: 10px;
  box-shadow: 0 4px 14px -4px rgba(4, 8, 18, 0.25),
              0 0 0 1px rgba(0, 45, 114, 0.12);
  white-space: normal;
  text-align: left;
  /* The text is non-interactive so it never blocks section clicks. */
  pointer-events: none;
  user-select: none;
}
/* The chip keeps its own click target so clicking the number still
   fires the hole action (the click listener is on the parent root). */
.tour-hole-label__chip {
  flex: 0 0 auto;
  width: 28px;
  height: 28px;
  border-radius: 50%;
  background: var(--apple-primary, #002D72);
  color: #fff;
  font-family: var(--font-display, inherit);
  font-size: 13px;
  font-weight: 700;
  display: flex;
  align-items: center;
  justify-content: center;
  box-shadow: 0 4px 14px -4px rgba(4, 8, 18, 0.55),
              0 0 0 4px rgba(104, 172, 229, 0.22);
  cursor: pointer;
  pointer-events: auto;
  transition: transform 0.2s ${CONSTANTS.SPRING},
              box-shadow 0.2s ${CONSTANTS.SMOOTH};
  user-select: none;
}
.tour-hole-label__chip:hover {
  transform: scale(1.08);
  box-shadow: 0 6px 18px -4px rgba(4, 8, 18, 0.6),
              0 0 0 6px rgba(104, 172, 229, 0.35);
}
/* On settled state, the callout stays at full opacity (so the user
   can still read the explanation while the action's effect persists),
   and the leader line dims to a moderate level — still visible, just
   less emphatic than before. */
.tour-hole-label.is-settled .tour-hole-label__chip {
  cursor: default;
}
@keyframes tour-chip-in {
  0%   { opacity: 0; transform: scale(0.6) translateY(-4px); }
  60%  { opacity: 1; transform: scale(1.08) translateY(0); }
  100% { opacity: 1; transform: scale(1) translateY(0); }
}
.tour-hole-label__svg {
  position: fixed;
  inset: 0;
  width: 100vw;
  height: 100vh;
  z-index: ${CONSTANTS.Z_LABEL_CONNECTOR};
  pointer-events: none;
}
.tour-hole-label__line {
  stroke: var(--apple-primary-on-dark, #68ACE5);
  stroke-width: 1.5;
  stroke-dasharray: 4 4;
  opacity: 0.85;
  transition: opacity 0.3s ${CONSTANTS.SMOOTH};
}
/* Settled leader line: visible but de-emphasized (between the
   previous 0.25 and the unsuppressed 0.85). */
.tour-hole-label__line.is-settled { opacity: 0.5; }

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
  transition: transform 0.18s ${CONSTANTS.SPRING};
}
.tour-panel.is-nudge {
  animation: tour-panel-nudge 0.42s ${CONSTANTS.SPRING};
}
@keyframes tour-panel-nudge {
  0%, 100% { transform: translateY(0); }
  40%      { transform: translateY(-6px); }
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
.tour-panel__hint {
  font-size: 12px;
  line-height: 1.4;
  color: var(--apple-text-secondary, inherit);
  margin-top: 2px;
  opacity: 0;
  max-height: 0;
  overflow: hidden;
  transition: opacity 0.3s ${CONSTANTS.SMOOTH},
              max-height 0.3s ${CONSTANTS.SMOOTH};
}
.tour-panel__hint.is-visible {
  opacity: 0.85;
  max-height: 40px;
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
  transition: transform 0.15s ${CONSTANTS.SMOOTH},
              background 0.15s ${CONSTANTS.SMOOTH},
              box-shadow 0.2s ${CONSTANTS.SMOOTH};
}
.tour-btn:hover { transform: translateY(-1px); }
.tour-btn--primary {
  background: var(--apple-primary, #002D72);
  color: #fff;
}
.tour-btn--primary:hover {
  background: var(--apple-primary-focus, #1a3d8f);
}
.tour-btn--breathing {
  animation: tour-btn-breath ${CONSTANTS.NEXT_BREATH_PERIOD_MS}ms ease-in-out infinite;
}
@keyframes tour-btn-breath {
  0%, 100% {
    transform: scale(1);
    box-shadow: 0 0 0 0 rgba(104, 172, 229, 0.45);
  }
  50% {
    transform: scale(1.03);
    box-shadow: 0 0 0 8px rgba(104, 172, 229, 0);
  }
}
.tour-btn--ghost {
  background: transparent;
  border-color: rgba(0, 45, 114, 0.25);
  color: var(--apple-primary, #002D72);
}
.tour-btn--ghost:hover { background: rgba(0, 45, 114, 0.06); }

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
  .tour-mask-svg,
  .tour-mask-svg rect.hole--blooming,
  .tour-hole-label,
  .tour-btn--primary,
  .tour-btn--breathing,
  .tour-cta {
    animation: none !important;
    transition: none !important;
  }
  .tour-mask-svg.is-fading-in { opacity: 1; }
  .tour-mask-svg.is-fading-out { opacity: 0; }
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
  .tour-canvas__hint {
    right: 12px;
    top: 22px;
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
