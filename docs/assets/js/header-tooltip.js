/* ============================================================
   Header tooltip — active-section detection
   Vanilla JS, no dependencies. Idempotent.
   Sets aria-current="page" on the .hp-icon whose href hash
   matches the section currently in the viewport.
   ============================================================ */
(function () {
  'use strict';

  function init() {
    var header = document.getElementById('app-header') || document.querySelector('.app-header');
    if (!header) return;

    // Reduced motion: signal CSS to disable hover lifts
    try {
      if (window.matchMedia && window.matchMedia('(prefers-reduced-motion: reduce)').matches) {
        document.body.classList.add('no-motion');
      }
    } catch (e) { /* matchMedia unsupported */ }

    var icons = Array.prototype.slice.call(header.querySelectorAll('.hp-icon'));
    if (icons.length === 0) return;

    // Map id -> .hp-icon element. Skip the CTA (external link, no in-page target).
    var byHash = {};
    icons.forEach(function (a) {
      var href = a.getAttribute('href') || '';
      var hash = href.split('#')[1];
      if (hash) byHash[hash] = a;
    });

    var sections = Object.keys(byHash)
      .map(function (id) { return document.getElementById(id); })
      .filter(function (el) { return !!el; });

    if (sections.length === 0) return;

    function setActive(activeHash) {
      icons.forEach(function (a) { a.removeAttribute('aria-current'); });
      if (activeHash && byHash[activeHash]) {
        byHash[activeHash].setAttribute('aria-current', 'page');
      }
    }

    if (!('IntersectionObserver' in window)) {
      return; // no-op on ancient browsers; CSS still works
    }

    var visible = new Map();
    var observer = new IntersectionObserver(function (entries) {
      entries.forEach(function (entry) {
        visible.set(entry.target.id, entry.intersectionRatio);
      });
      // Pick the section with the highest intersection ratio
      var bestId = null;
      var bestRatio = 0;
      visible.forEach(function (ratio, id) {
        if (ratio > bestRatio) { bestRatio = ratio; bestId = id; }
      });
      if (bestId) setActive(bestId);
    }, {
      root: null,
      rootMargin: '-40% 0px -40% 0px',
      threshold: [0, 0.25, 0.5, 0.75, 1]
    });

    sections.forEach(function (sec) { observer.observe(sec); });
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
})();
