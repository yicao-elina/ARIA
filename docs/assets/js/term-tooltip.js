/* ============================================================
   term-tooltip.js — portal-based popover for inline glossary
   terms (.term-tip).

   The CSS ::after / ::before popover gets clipped by ancestor
   overflow:hidden (notably .glass-card, .callout, .detail-toggle),
   and even with z-index:1000 it can be visually overrun by sibling
   elements that have their own stacking context. The fix is to
   render the popover in <body> via position:fixed, so it lives in
   the page-level stacking context and is never clipped by an
   ancestor's overflow.

   Hover and keyboard focus both open the popover; leaving the term
   or pressing Esc closes it. The .term-tip--below modifier flips
   the popover below the term (used for terms near the top of a
   card, so the popover doesn't collide with the card's title).
   ============================================================ */
(function () {
  'use strict';

  var ACTIVE_ATTR = 'data-term-tooltip-active';
  var BELOW_CLASS = 'term-tip--below';
  var RIGHT_CLASS = 'term-tip--right';
  var VIEWPORT_PAD = 8; // px from viewport edge

  function getTip(tip) {
    return tip.getAttribute('data-tip') || '';
  }

  function buildPopover() {
    var el = document.createElement('div');
    el.className = 'term-tooltip-popover';
    el.setAttribute('role', 'tooltip');
    el.setAttribute(ACTIVE_ATTR, 'true');
    return el;
  }

  function positionPopover(popover, tip) {
    var rect = tip.getBoundingClientRect();
    var isBelow = tip.classList.contains(BELOW_CLASS);

    // Measure after content is set, so width follows the text
    popover.style.left = '0px';
    popover.style.top = '0px';
    var pw = popover.offsetWidth;
    var ph = popover.offsetHeight;

    // Horizontal: center on the term, but clamp to viewport
    var cx = rect.left + rect.width / 2;
    var left = cx - pw / 2;
    left = Math.max(VIEWPORT_PAD, Math.min(left, window.innerWidth - pw - VIEWPORT_PAD));

    var isRight = tip.classList.contains(RIGHT_CLASS);
    if (isRight) {
      // Anchor to the right side of the term, vertically centered
      left = rect.right + 12;
      // Flip to the left side if it would overflow the right edge
      if (left + pw > window.innerWidth - VIEWPORT_PAD) {
        left = rect.left - pw - 12;
        popover.classList.add('term-tooltip-popover--left');
        popover.classList.remove('term-tooltip-popover--right');
      } else {
        popover.classList.add('term-tooltip-popover--right');
        popover.classList.remove('term-tooltip-popover--left');
      }
      left = Math.max(VIEWPORT_PAD, Math.min(left, window.innerWidth - pw - VIEWPORT_PAD));
    }

    // Vertical: above by default; flip below if requested, or if
    // there's not enough room above.
    var top;
    if (isBelow) {
      top = rect.bottom + 10;
      popover.classList.add('term-tooltip-popover--below');
      popover.classList.remove('term-tooltip-popover--above');
      if (top + ph > window.innerHeight - VIEWPORT_PAD) {
        // Not enough room below either — flip above
        top = rect.top - ph - 10;
        popover.classList.add('term-tooltip-popover--above');
        popover.classList.remove('term-tooltip-popover--below');
      }
    } else if (isRight) {
      // Vertically center the popover on the term
      top = rect.top + rect.height / 2 - ph / 2;
    } else {
      top = rect.top - ph - 10;
      popover.classList.add('term-tooltip-popover--above');
      popover.classList.remove('term-tooltip-popover--below');
      if (top < VIEWPORT_PAD) {
        top = rect.bottom + 10;
        popover.classList.add('term-tooltip-popover--below');
        popover.classList.remove('term-tooltip-popover--above');
      }
    }
    top = Math.max(VIEWPORT_PAD, Math.min(top, window.innerHeight - ph - VIEWPORT_PAD));

    popover.style.left = Math.round(left) + 'px';
    popover.style.top = Math.round(top) + 'px';
  }

  function show(tip) {
    if (tip.getAttribute(ACTIVE_ATTR) === 'true') return;
    tip.setAttribute(ACTIVE_ATTR, 'true');
    var popover = buildPopover();
    popover.textContent = getTip(tip);
    document.body.appendChild(popover);
    // Defer measurement so layout is final
    requestAnimationFrame(function () {
      positionPopover(popover, tip);
    });
    // Keep on the same y when window resizes
    window.addEventListener('resize', reposition);
    window.addEventListener('scroll', reposition, true);
  }

  function reposition() {
    var popover = document.querySelector('.term-tooltip-popover');
    if (!popover) return;
    var tip = document.querySelector('.term-tip[' + ACTIVE_ATTR + '="true"]');
    if (!tip) return;
    positionPopover(popover, tip);
  }

  function hide(tip) {
    if (tip.getAttribute(ACTIVE_ATTR) !== 'true') return;
    tip.removeAttribute(ACTIVE_ATTR);
    var popover = document.querySelector('.term-tooltip-popover');
    if (popover) popover.remove();
    window.removeEventListener('resize', reposition);
    window.removeEventListener('scroll', reposition, true);
  }

  function init() {
    var tips = document.querySelectorAll('.term-tip');
    if (tips.length === 0) return;
    document.documentElement.classList.add('has-term-tooltip');
    tips.forEach(function (tip) {
      tip.addEventListener('mouseenter', function () { show(tip); });
      tip.addEventListener('mouseleave', function () { hide(tip); });
      tip.addEventListener('focus', function () { show(tip); });
      tip.addEventListener('blur', function () { hide(tip); });
    });
    document.addEventListener('keydown', function (e) {
      if (e.key === 'Escape') {
        var active = document.querySelector('.term-tip[' + ACTIVE_ATTR + '="true"]');
        if (active) {
          hide(active);
          active.blur();
        }
      }
    });
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
})();
