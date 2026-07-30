// Drives the hero scroll scene: sets --scene-progress (0..1) on the
// hero .tile__content, and hands #hero-scene off between position:
// fixed (resting/scrolling-past phase) and position: absolute (landed
// in its reserved slot) as the user scrolls. All visual interpolation
// (converge + sharpen) lives in hero-scene.css via calc(var(--scene-
// progress) * ...) — this file only ever writes that one custom
// property, toggles #hero-scene's position, and opens .hero-scene__card
// once past a threshold (never overriding a manual user toggle).
//
// Model:
// - restTop = the screen Y where #hero-scene rests, measured from the
//   actual rendered position of the subtitle/byline block (not
//   hardcoded), so it self-adjusts to however the title wraps.
// - #hero-scene-slot is a real, empty, in-flow spacer placed right
//   before .hero-lead; its document-absolute Y (slotDocTop = its
//   rect.top + scrollY, invariant across scroll) is the scroll position
//   at which the slot's screen position reaches restTop.
// - progress = scrollY / (slotDocTop - restTop), eased with t*t so it
//   starts slow and accelerates past roughly the halfway point,
//   reaching 1 exactly when the slot reaches restTop.
// - Once the slot's rect.top <= restTop, #hero-scene "lands": switched
//   from fixed to absolute (relative to .tile--hero), with `top` set
//   from the live viewport rects at that instant so it lands exactly
//   where it already visually was. Scrolling back above that point
//   reverses the handoff.
(function () {
  'use strict';

  var scene = document.getElementById('hero-scene');
  var slot = document.getElementById('hero-scene-slot');
  if (!scene || !slot) return;

  var tileHero = scene.closest('.tile--hero');
  // --scene-progress must be set on an ancestor common to BOTH #hero-scene
  // (a sibling of .tile__content, not a descendant — see the fixed-overlay
  // note above) and .hero-scene__card (inside .tile__content/.hero-lead),
  // or CSS custom-property inheritance won't reach one of them. .tile--hero
  // is the nearest such ancestor.
  var progressRoot = tileHero || scene;

  var card = progressRoot.querySelector('.hero-scene__card');
  var summary = card ? card.querySelector('summary') : null;
  var cardManuallyToggled = false;
  var isProgrammaticOpen = false;

  if (summary) {
    summary.addEventListener('click', function () {
      if (isProgrammaticOpen) return;
      cardManuallyToggled = true;
    });
  }

  // detail-toggle.js owns the actual open/close animation (an .is-open
  // class + explicit max-height on .detail-toggle__body) and only runs
  // it in response to a real click on <summary> — setting `.open`
  // directly here would flip the native attribute while leaving the
  // body visually collapsed (max-height: 0), desyncing the two and
  // making the user's next manual click toggle backwards. Firing a
  // real click keeps this in sync (same pattern as tour.js's
  // openDetails()).
  function autoOpenCard() {
    if (!card || !summary || card.open) return;
    isProgrammaticOpen = true;
    summary.click();
    isProgrammaticOpen = false;
  }

  function clamp(value, min, max) {
    return Math.max(min, Math.min(max, value));
  }

  function land() {
    var slotRect = slot.getBoundingClientRect();
    var tileRect = tileHero.getBoundingClientRect();
    scene.style.position = 'absolute';
    scene.style.top = (slotRect.top - tileRect.top) + 'px';
    scene.classList.add('is-landed');
  }

  var reduceMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;

  if (reduceMotion) {
    land();
    progressRoot.style.setProperty('--scene-progress', 1);
    autoOpenCard();
    return;
  }

  var restTop = 280;
  var landed = false;

  // Measures where #hero-scene should rest: vertically centered on the
  // subtitle-through-legend block, so it reads as flanking that text.
  // Uses doc-absolute positions (rect.top + scrollY, invariant across
  // scroll) rather than raw live rects — raw rects move every scroll
  // frame along with the text itself, which would make restTop drift
  // instead of staying the fixed reference point it needs to be. Only
  // call this on load/resize, never per scroll frame.
  function computeRestTop() {
    var subtitle = document.querySelector('.hero-subtitle');
    var legend = document.querySelector('.hero-authors-legend');
    if (!subtitle || !legend) return;
    var subDocTop = subtitle.getBoundingClientRect().top + window.scrollY;
    var legendDocBottom = legend.getBoundingClientRect().bottom + window.scrollY;
    var sceneHeight = scene.getBoundingClientRect().height || 220;
    var midpoint = (subDocTop + legendDocBottom) / 2;
    restTop = midpoint - sceneHeight / 2;
    if (!landed) {
      scene.style.top = restTop + 'px';
    }
  }

  function unland() {
    scene.style.position = 'fixed';
    scene.style.top = restTop + 'px';
    scene.classList.remove('is-landed');
  }

  var ticking = false;

  function updateProgress() {
    ticking = false;

    var slotRect = slot.getBoundingClientRect();
    var slotDocTop = slotRect.top + window.scrollY;
    var landDistance = slotDocTop - restTop;
    var raw = landDistance > 0 ? clamp(window.scrollY / landDistance, 0, 1) : 1;
    var eased = raw * raw;
    progressRoot.style.setProperty('--scene-progress', String(eased));

    if (slotRect.top <= restTop) {
      if (!landed) {
        landed = true;
        land();
      }
    } else if (landed) {
      landed = false;
      unland();
    }

    if (!cardManuallyToggled && eased > 0.6) {
      autoOpenCard();
    }
  }

  function onScroll() {
    if (!ticking) {
      ticking = true;
      requestAnimationFrame(updateProgress);
    }
  }

  function onResize() {
    computeRestTop();
    onScroll();
  }

  window.addEventListener('scroll', onScroll, { passive: true });
  window.addEventListener('resize', onResize, { passive: true });
  computeRestTop();
  updateProgress();
})();
