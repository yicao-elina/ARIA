/* ============================================================
   Reveal-on-scroll observer
   Marks .reveal elements with .is-visible the first time they
   intersect the viewport. Groups elements by their parent's
   [data-reveal-group] attribute and staggers transition-delay
   inside each group. Honors prefers-reduced-motion and
   degrades gracefully when IntersectionObserver is missing.
   Idempotent.
   ============================================================ */
(function () {
  'use strict';

  var SELECTOR = '.reveal';
  var STAGGER_MS = 60;

  function reducedMotion() {
    return window.matchMedia &&
           window.matchMedia('(prefers-reduced-motion: reduce)').matches;
  }

  function applyStagger(items) {
    var groups = {};
    items.forEach(function (el) {
      var parent = el.parentElement;
      var key = (parent && parent.dataset && parent.dataset.revealGroup)
        ? parent.dataset.revealGroup
        : 'default';
      if (!groups[key]) groups[key] = [];
      groups[key].push(el);
    });
    Object.keys(groups).forEach(function (key) {
      groups[key].forEach(function (el, i) {
        el.style.transitionDelay = (i * STAGGER_MS) + 'ms';
      });
    });
  }

  function revealAll(items) {
    items.forEach(function (el) { el.classList.add('is-visible'); });
  }

  function init() {
    var items = Array.prototype.slice.call(document.querySelectorAll(SELECTOR));
    if (!items.length) return;

    if (reducedMotion()) {
      document.body.classList.add('no-motion');
      revealAll(items);
      return;
    }

    applyStagger(items);

    if (!('IntersectionObserver' in window)) {
      revealAll(items);
      return;
    }

    var io = new IntersectionObserver(function (entries, observer) {
      entries.forEach(function (entry) {
        if (entry.isIntersecting) {
          entry.target.classList.add('is-visible');
          observer.unobserve(entry.target);
        }
      });
    }, {
      rootMargin: '0px 0px -10% 0px',
      threshold: 0.1
    });

    items.forEach(function (el) { io.observe(el); });
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
})();
