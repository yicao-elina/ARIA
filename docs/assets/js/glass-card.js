/* ============================================================
   glass-card.js
   Cursor spotlight + idle float delay for .glass-card elements.
   Sets --mx / --my (percent) for the radial-gradient cursor glow
   consumed by glass.css. Also assigns a randomized --float-delay
   so the CSS keyframe animation drifts cards out of lockstep.

   Notes:
   - The 3D tilt (--tilt-x / --tilt-y) has been removed — the
     rotateX/rotateY hover effect was too theatrical for a
     research-paper aesthetic. The refined micro-motion is now
     a slow translateY drift (see @keyframes glass-float in
     glass.css) plus a small lift on hover.
   - No-ops on touch devices and when prefers-reduced-motion: reduce.
   - Adds body.no-motion / body.no-spotlight as global kill-switches.
   - Idempotent: safe to call multiple times.
   - Vanilla JS, no framework, no jQuery.
   ============================================================ */
(function () {
  "use strict";

  var SELECTOR = ".glass-card";
  var SPOTLIGHT_SELECTOR = ".glass-card:not(.glass-card--no-spotlight)";

  function reducedMotion() {
    return window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  }

  function isTouchDevice() {
    return window.matchMedia("(hover: none)").matches || ("ontouchstart" in window);
  }

  function init() {
    var cards = document.querySelectorAll(SELECTOR);
    if (!cards.length) return;

    if (reducedMotion()) document.body.classList.add("no-motion");
    if (isTouchDevice()) document.body.classList.add("no-spotlight");

    var motionOff = reducedMotion() || isTouchDevice();

    // Assign each card a randomized float delay so the CSS keyframe
    // animation drifts them out of lockstep. Negative delays start
    // each card mid-animation, avoiding a synchronized "everyone
    // lifts at once" effect on first paint. 0–6.5s range matches
    // the 6.5s float duration in glass.css.
    for (var i = 0; i < cards.length; i++) {
      var card = cards[i];
      if (card.classList.contains("glass-card--no-float")) continue;
      var delay = -(Math.random() * 6.5);
      card.style.setProperty("--float-delay", delay.toFixed(2) + "s");
    }

    if (motionOff) return; // Skip the spotlight listener entirely on touch / reduced-motion.

    // Spotlight: document-level pointermove (event delegation).
    document.addEventListener("pointermove", function (e) {
      var target = e.target.closest(SPOTLIGHT_SELECTOR);
      if (!target) return;
      var rect = target.getBoundingClientRect();
      var xPct = ((e.clientX - rect.left) / rect.width) * 100;
      var yPct = ((e.clientY - rect.top) / rect.height) * 100;
      target.style.setProperty("--mx", xPct.toFixed(2) + "%");
      target.style.setProperty("--my", yPct.toFixed(2) + "%");
    }, { passive: true });
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }
})();
