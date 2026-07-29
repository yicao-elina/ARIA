/**
 * tour.js — Guided, operational walkthrough of the ARIA site.
 *
 * Self-contained page chrome: a floating glass-card control panel that
 * scrolls/highlights each major section in sequence and invites the
 * visitor to actually try the interactive demos, rather than just
 * reading past them.
 *
 * No dependencies. Self-initializes on DOMContentLoaded (guarded for
 * the case the script executes after the event already fired, since
 * it is loaded with `defer`).
 */
(function () {
  "use strict";

  const STOPS = [
    {
      id: "problem",
      title: "The Problem: Contextual Tunneling",
      body: "Compare a baseline LLM against a naive KG+LLM system below — the naive system over-anchors on partial evidence. Try the demo to see the failure mode ARIA is built to prevent.",
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
    },
    {
      id: "kg-section",
      title: "Knowledge Graph Explorer",
      body: "Explore the interactive causal knowledge graph — filter by material, PSP layer, or edge type. We've also opened the “Advanced settings” panel below the graph, which discloses exactly which KG file this demo loads.",
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
    },
    {
      id: "results",
      title: "Results",
      body: "The full benchmark results — chart and table — live here. Worth a scan, but we'll keep moving since the next sections are more hands-on.",
    },
    {
      id: "robustness",
      title: "Robustness & Ablation",
      body: "Drag the slider below to simulate progressively deleting knowledge-graph edges and watch how ARIA absorbs the damage compared to a naive KG baseline.",
    },
    {
      id: "trace-audit",
      title: "Causal Trace Audit",
      body: "Every ARIA answer ships with an auditable, step-by-step causal trace. Walk through the example below to see how a result can be verified end to end.",
    },
  ];

  const HIGHLIGHT_CLASS = "tour-highlight";

  class SiteTour {
    constructor(stops) {
      this.stops = stops.filter((stop) => document.getElementById(stop.id));
      this.index = -1;
      this.active = false;
      this.panel = null;
      this._onKeydown = this._onKeydown.bind(this);
      this._injectStyles();
    }

    start() {
      if (!this.stops.length) return;
      this.active = true;
      this.index = 0;
      this._buildPanel();
      document.addEventListener("keydown", this._onKeydown);
      this._goTo(0);
    }

    end() {
      if (!this.active) return;
      this.active = false;
      this._clearHighlight();
      const current = this.stops[this.index];
      if (current && typeof current.onLeave === "function") {
        current.onLeave(document.getElementById(current.id));
      }
      if (this.panel) {
        this.panel.remove();
        this.panel = null;
      }
      document.removeEventListener("keydown", this._onKeydown);
    }

    next() {
      if (this.index >= this.stops.length - 1) {
        this.end();
        return;
      }
      this._goTo(this.index + 1);
    }

    back() {
      if (this.index <= 0) return;
      this._goTo(this.index - 1);
    }

    _goTo(nextIndex) {
      const prevStop = this.stops[this.index];
      if (prevStop) {
        this._clearHighlight();
        if (typeof prevStop.onLeave === "function") {
          prevStop.onLeave(document.getElementById(prevStop.id));
        }
      }

      this.index = nextIndex;
      const stop = this.stops[this.index];
      const section = document.getElementById(stop.id);
      if (!section) {
        this.next();
        return;
      }

      const reduceMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
      section.scrollIntoView({
        behavior: reduceMotion ? "auto" : "smooth",
        block: "center",
      });
      section.classList.add(HIGHLIGHT_CLASS);

      if (typeof stop.onEnter === "function") {
        stop.onEnter(section);
      }

      this._renderPanel();
    }

    _clearHighlight() {
      document.querySelectorAll("." + HIGHLIGHT_CLASS).forEach((el) => {
        el.classList.remove(HIGHLIGHT_CLASS);
      });
    }

    _buildPanel() {
      const panel = document.createElement("div");
      panel.className = "tour-panel glass-card";
      panel.setAttribute("role", "dialog");
      panel.setAttribute("aria-label", "Guided tour");
      document.body.appendChild(panel);
      this.panel = panel;
    }

    _renderPanel() {
      if (!this.panel) return;
      const stop = this.stops[this.index];
      const total = this.stops.length;
      const step = this.index + 1;
      const isLast = step === total;

      this.panel.innerHTML = "";

      const progress = document.createElement("div");
      progress.className = "tour-panel__progress";
      progress.textContent = "Step " + step + " of " + total;
      this.panel.appendChild(progress);

      const title = document.createElement("div");
      title.className = "tour-panel__title";
      title.textContent = stop.title;
      this.panel.appendChild(title);

      const body = document.createElement("p");
      body.className = "tour-panel__body";
      body.textContent = stop.body;
      this.panel.appendChild(body);

      const controls = document.createElement("div");
      controls.className = "tour-panel__controls";

      const skipBtn = document.createElement("button");
      skipBtn.type = "button";
      skipBtn.className = "tour-btn tour-btn--ghost";
      skipBtn.textContent = "End Tour";
      skipBtn.addEventListener("click", () => this.end());
      controls.appendChild(skipBtn);

      const spacer = document.createElement("div");
      spacer.className = "tour-panel__spacer";
      controls.appendChild(spacer);

      if (step > 1) {
        const backBtn = document.createElement("button");
        backBtn.type = "button";
        backBtn.className = "tour-btn tour-btn--ghost";
        backBtn.textContent = "Back";
        backBtn.addEventListener("click", () => this.back());
        controls.appendChild(backBtn);
      }

      const nextBtn = document.createElement("button");
      nextBtn.type = "button";
      nextBtn.className = "tour-btn tour-btn--primary";
      nextBtn.textContent = isLast ? "Finish" : "Next";
      nextBtn.addEventListener("click", () => this.next());
      controls.appendChild(nextBtn);

      this.panel.appendChild(controls);
    }

    _onKeydown(event) {
      if (event.key === "Escape") {
        this.end();
      }
    }

    _injectStyles() {
      if (document.getElementById("tour-styles")) return;
      const style = document.createElement("style");
      style.id = "tour-styles";
      style.textContent = `
.tour-panel {
  position: fixed;
  right: 20px;
  bottom: 20px;
  z-index: 2000;
  width: min(340px, calc(100vw - 40px));
  padding: 18px 20px;
  display: flex;
  flex-direction: column;
  gap: 8px;
}
.tour-panel__progress {
  font-size: 12px;
  font-weight: 600;
  letter-spacing: 0.03em;
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
.tour-panel__body {
  font-size: 13.5px;
  line-height: 1.45;
  margin: 0;
  color: var(--apple-text-secondary, inherit);
}
.tour-panel__controls {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-top: 8px;
}
.tour-panel__spacer {
  flex: 1 1 auto;
}
.tour-btn {
  font-family: inherit;
  font-size: 13px;
  font-weight: 600;
  padding: 7px 14px;
  border-radius: var(--radius-pill, 9999px);
  border: 1px solid transparent;
  cursor: pointer;
  transition: transform 0.15s ease, background 0.15s ease;
}
.tour-btn:hover {
  transform: translateY(-1px);
}
.tour-btn--primary {
  background: var(--apple-primary, #002D72);
  color: #fff;
}
.tour-btn--primary:hover {
  background: var(--apple-primary-focus, #1a3d8f);
}
.tour-btn--ghost {
  background: transparent;
  border-color: rgba(0, 45, 114, 0.25);
  color: var(--apple-primary, #002D72);
}
.tour-btn--ghost:hover {
  background: rgba(0, 45, 114, 0.06);
}
.tour-highlight {
  position: relative;
  outline: 3px solid var(--apple-primary-on-dark, #68ACE5);
  outline-offset: 6px;
  border-radius: var(--radius-md, 11px);
  box-shadow: 0 0 0 8px rgba(104, 172, 229, 0.15);
  transition: outline-color 0.2s ease, box-shadow 0.2s ease;
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
    }
  }

  function init() {
    const tour = new SiteTour(STOPS);
    const button = document.getElementById("tour-start-btn");
    if (button) {
      button.addEventListener("click", (event) => {
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
