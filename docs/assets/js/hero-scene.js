// Drives the hero scroll scene: sets --scene-progress (0..1) on
// #hero-scene as the user scrolls through its 220vh track. All visual
// interpolation lives in hero-scene.css via calc(var(--scene-progress) * ...)
// — this file only ever writes that one custom property, plus toggling
// .hero-scene__card open once past a threshold (never overriding a
// manual user toggle).
(function () {
  'use strict';

  var scene = document.getElementById('hero-scene');
  if (!scene) return;

  var card = scene.querySelector('.hero-scene__card');
  var summary = card ? card.querySelector('summary') : null;
  var cardManuallyToggled = false;

  if (summary) {
    summary.addEventListener('click', function () {
      cardManuallyToggled = true;
    });
  }

  var reduceMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;

  function clamp(value, min, max) {
    return Math.max(min, Math.min(max, value));
  }

  if (reduceMotion) {
    scene.style.setProperty('--scene-progress', 1);
    if (card && !card.open) card.open = true;
    return;
  }

  var ticking = false;

  function updateProgress() {
    ticking = false;
    var rect = scene.getBoundingClientRect();
    var trackable = rect.height - window.innerHeight;
    var progress = trackable > 0 ? clamp(-rect.top / trackable, 0, 1) : 1;
    scene.style.setProperty('--scene-progress', String(progress));

    if (card && !cardManuallyToggled && progress > 0.6 && !card.open) {
      card.open = true;
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
