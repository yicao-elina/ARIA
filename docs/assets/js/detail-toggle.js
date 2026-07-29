/* Hover-to-preview behavior for .detail-toggle <details> panels.
   Hovering the <summary> for a moment opens the panel without a click,
   mirroring the hp-tooltip hover reveal used elsewhere on the page.
   Once a user clicks (pinning it open/closed deliberately), hover no
   longer auto-closes it — the click always wins. */
(function () {
  'use strict';

  var HOVER_DELAY = 260;

  document.querySelectorAll('.detail-toggle > summary').forEach(function (summary) {
    var details = summary.parentElement;
    var timer = null;
    // Panels marked open in the HTML (e.g. the default-expanded Tier 1
    // example) start pinned so a stray hover-out doesn't collapse them.
    var pinned = details.open;

    summary.addEventListener('click', function () {
      pinned = true;
    });

    summary.addEventListener('mouseenter', function () {
      if (details.open) return;
      timer = window.setTimeout(function () {
        details.open = true;
      }, HOVER_DELAY);
    });

    summary.addEventListener('mouseleave', function () {
      window.clearTimeout(timer);
      if (!pinned) {
        details.open = false;
      }
    });

    summary.addEventListener('focus', function () {
      details.open = true;
    });
  });
})();
