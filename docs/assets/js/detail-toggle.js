/* Hover-to-open behavior for .detail-toggle <details> panels.
   Hovering the <summary> for a moment opens the panel without a click,
   mirroring the hp-tooltip hover reveal used elsewhere on the page.
   Once opened (by hover or click) it STAYS open — moving the mouse
   away never auto-collapses it. The only way to close it again is an
   explicit click on the summary. */
(function () {
  'use strict';

  var HOVER_DELAY = 260;

  document.querySelectorAll('.detail-toggle > summary').forEach(function (summary) {
    var details = summary.parentElement;
    var timer = null;

    summary.addEventListener('mouseenter', function () {
      if (details.open) return;
      timer = window.setTimeout(function () {
        details.open = true;
      }, HOVER_DELAY);
    });

    summary.addEventListener('mouseleave', function () {
      window.clearTimeout(timer);
    });

    summary.addEventListener('focus', function () {
      details.open = true;
    });
  });
})();
