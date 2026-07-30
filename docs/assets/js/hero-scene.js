// Drives the hero scroll scene: sets --scene-progress (0..1) on
// #hero-scene as the user scrolls through its 220vh track. All visual
// interpolation lives in hero-scene.css via calc(var(--scene-progress) * ...)
// — this file only ever writes that one custom property, plus opening
// .hero-scene__card once past a threshold (never overriding a manual
// user toggle).
(function () {
  'use strict';

  var scene = document.getElementById('hero-scene');
  if (!scene) return;

  var card = scene.querySelector('.hero-scene__card');
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

  var reduceMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;

  function clamp(value, min, max) {
    return Math.max(min, Math.min(max, value));
  }

  if (reduceMotion) {
    scene.style.setProperty('--scene-progress', 1);
    autoOpenCard();
    return;
  }

  var ticking = false;

  function updateProgress() {
    ticking = false;
    var rect = scene.getBoundingClientRect();
    var trackable = rect.height - window.innerHeight;
    var progress = trackable > 0 ? clamp(-rect.top / trackable, 0, 1) : 1;
    scene.style.setProperty('--scene-progress', String(progress));

    if (!cardManuallyToggled && progress > 0.6) {
      autoOpenCard();
    }
  }

  function onScrollOrResize() {
    if (!ticking) {
      ticking = true;
      requestAnimationFrame(updateProgress);
    }
  }

  window.addEventListener('scroll', onScrollOrResize, { passive: true });
  window.addEventListener('resize', onScrollOrResize, { passive: true });
  updateProgress();
})();
