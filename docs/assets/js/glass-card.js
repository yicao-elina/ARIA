/* ============================================================
   glass-card.js
   Cursor spotlight + 3D tilt for .glass-card elements.
   Sets --mx / --my (percent) and --tilt-x / --tilt-y (deg) as
   CSS custom properties consumed by glass.css.
   - No-ops on touch devices and when prefers-reduced-motion: reduce.
   - Adds body.no-motion / body.no-spotlight as global kill-switches.
   - Idempotent: safe to call multiple times.
   - Vanilla JS, no framework, no jQuery.
   ============================================================ */
(function () {
  "use strict";

  var MAX_TILT = 8;            // degrees, baseline for small cards
  var SELECTOR = ".glass-card";
  var SPOTLIGHT_SELECTOR = ".glass-card:not(.glass-card--no-spotlight)";
  var TILT_SELECTOR = ".glass-card:not(.glass-card--no-tilt)";

  function reducedMotion() {
    return window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  }

  function isTouchDevice() {
    return window.matchMedia("(hover: none)").matches || ("ontouchstart" in window);
  }

  // Size-proportional tilt cap. Larger cards use a smaller angle so
  // the 3D effect stays subtle and refined instead of feeling like the
  // card is wobbling. Recomputed once per card and cached in dataset
  // so we don't hit getBoundingClientRect on every pointermove.
  function computeMaxTilt(width) {
    if (width < 300) return 8;
    if (width < 600) return 6;
    if (width < 900) return 4;
    return 3;
  }

  function init() {
    var cards = document.querySelectorAll(SELECTOR);
    if (!cards.length) return;

    if (reducedMotion()) document.body.classList.add("no-motion");
    if (isTouchDevice()) document.body.classList.add("no-spotlight");

    var motionOff = reducedMotion() || isTouchDevice();

    // Spotlight: document-level pointermove (event delegation).
    document.addEventListener("pointermove", function (e) {
      if (motionOff) return;
      var target = e.target.closest(SPOTLIGHT_SELECTOR);
      if (!target) return;
      var rect = target.getBoundingClientRect();
      var xPct = ((e.clientX - rect.left) / rect.width) * 100;
      var yPct = ((e.clientY - rect.top) / rect.height) * 100;
      target.style.setProperty("--mx", xPct.toFixed(2) + "%");
      target.style.setProperty("--my", yPct.toFixed(2) + "%");
    }, { passive: true });

    // 3D tilt: per-card pointermove + pointerleave.
    for (var i = 0; i < cards.length; i++) {
      (function (card) {
        if (motionOff) return;
        if (!card.matches(TILT_SELECTOR)) return;

        // Compute and cache the size-based tilt cap once per card.
        // Recomputed on resize so reflows don't strand a stale cap.
        var cachedMax = NaN;
        function refreshMax() {
          var w = card.getBoundingClientRect().width;
          var cap = computeMaxTilt(w);
          cachedMax = cap;
          card.dataset.maxTilt = String(cap);
        }
        refreshMax();
        window.addEventListener("resize", refreshMax, { passive: true });

        card.addEventListener("pointermove", function (e) {
          var rect = card.getBoundingClientRect();
          var dx = (e.clientX - (rect.left + rect.width / 2)) / (rect.width / 2);
          var dy = (e.clientY - (rect.top + rect.height / 2)) / (rect.height / 2);
          var cx = Math.max(-1, Math.min(1, dx));
          var cy = Math.max(-1, Math.min(1, -dy));   // invert so up-tilt is positive
          var tilt = isNaN(cachedMax) ? MAX_TILT : cachedMax;
          card.style.setProperty("--tilt-x", (cx * tilt).toFixed(2) + "deg");
          card.style.setProperty("--tilt-y", (cy * tilt).toFixed(2) + "deg");
        });

        card.addEventListener("pointerleave", function () {
          card.style.setProperty("--tilt-x", "0deg");
          card.style.setProperty("--tilt-y", "0deg");
        });
      })(cards[i]);
    }
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }
})();
