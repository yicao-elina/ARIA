/* Springy open/close for .detail-toggle <details> panels.
   Native <details> toggling is an instant, one-way snap (no way to
   animate closing), so this drives open/close manually: max-height,
   opacity, and a scaleY/translateY transform are toggled via the
   .is-open class, and glossary.css gives those properties a spring
   (overshoot) transition — the SAME bounce plays on open and on
   close.
   Hover-to-open behavior is preserved: hovering the <summary> for a
   moment opens the panel without a click. Once opened it stays open
   until an explicit click on the summary closes it. */
(function () {
  'use strict';

  var HOVER_DELAY = 260;

  document.querySelectorAll('.detail-toggle').forEach(function (details) {
    var summary = details.querySelector(':scope > summary');
    var body = details.querySelector(':scope > .detail-toggle__body');
    if (!summary || !body) return;

    var hoverTimer = null;
    var closeListener = null;

    // Start already-open panels (e.g. Tier 1's default-open example)
    // in the open state with no transition, so nothing animates in
    // on first paint.
    if (details.hasAttribute('open')) {
      body.classList.add('is-open');
      body.style.maxHeight = body.scrollHeight + 'px';
    }

    function openPanel() {
      if (details.open) return;
      details.open = true;
      // Force layout so the browser has a committed "closed" state
      // to transition away from before we flip to open.
      void body.offsetHeight;
      body.classList.add('is-open');
      body.style.maxHeight = body.scrollHeight + 'px';
    }

    function closePanel() {
      if (!details.open) return;
      // Pin the current rendered height explicitly (was likely
      // unbounded after opening) so the collapse has a real
      // starting point to transition from.
      body.style.maxHeight = body.scrollHeight + 'px';
      void body.offsetHeight;
      body.classList.remove('is-open');
      body.style.maxHeight = '0px';

      if (closeListener) body.removeEventListener('transitionend', closeListener);
      closeListener = function (e) {
        if (e.target !== body || e.propertyName !== 'max-height') return;
        if (!body.classList.contains('is-open')) details.open = false;
        body.removeEventListener('transitionend', closeListener);
        closeListener = null;
      };
      body.addEventListener('transitionend', closeListener);
    }

    summary.addEventListener('click', function (e) {
      e.preventDefault();
      window.clearTimeout(hoverTimer);
      if (details.open) {
        closePanel();
      } else {
        openPanel();
      }
    });

    summary.addEventListener('mouseenter', function () {
      if (details.open) return;
      hoverTimer = window.setTimeout(openPanel, HOVER_DELAY);
    });

    summary.addEventListener('mouseleave', function () {
      window.clearTimeout(hoverTimer);
    });

    summary.addEventListener('focus', function () {
      openPanel();
    });

    // Keep an open panel's max-height accurate if content or layout
    // reflows (e.g. window resize, webfont load) after it settles.
    window.addEventListener('resize', function () {
      if (details.open && body.classList.contains('is-open')) {
        body.style.maxHeight = body.scrollHeight + 'px';
      }
    });
  });
})();
