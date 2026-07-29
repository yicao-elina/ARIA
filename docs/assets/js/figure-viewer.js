/**
 * ARIA — Figure Viewer + Lightbox + Clickable Hotspots
 *
 * - Click an image in a .figure-block to open a full-size lightbox (PNG).
 * - Each .fig-hotspot scrolls the page to the matching section, then pulses
 *   the section's <section class="tile"> so users see where they landed.
 * - Hotspots gracefully degrade: if the section is missing, they just log.
 *
 * Exposes:  window.ARIA.figureViewer.init()
 */
;(function () {
  'use strict';

  function openLightbox(src, alt) {
    if (!src) return;
    var lb = document.querySelector('.fig-lightbox');
    if (!lb) {
      lb = document.createElement('div');
      lb.className = 'fig-lightbox';
      lb.setAttribute('role', 'dialog');
      lb.setAttribute('aria-modal', 'true');
      lb.setAttribute('aria-label', alt || 'Figure');
      lb.innerHTML =
        '<button class="fig-lightbox__close" type="button" aria-label="Close (Esc)">\u00d7</button>' +
        '<img class="fig-lightbox__image" alt="' + (alt || '').replace(/"/g, '&quot;') + '" />' +
        '<div class="fig-lightbox__caption"></div>';
      document.body.appendChild(lb);
      lb.addEventListener('click', function (e) {
        if (e.target === lb) closeLightbox();
      });
      lb.querySelector('.fig-lightbox__close').addEventListener('click', closeLightbox);
      document.addEventListener('keydown', function (e) {
        if (e.key === 'Escape' && lb.classList.contains('is-open')) closeLightbox();
      });
    }
    var img = lb.querySelector('.fig-lightbox__image');
    img.src = src;
    img.alt = alt || '';
    lb.querySelector('.fig-lightbox__caption').textContent = alt || '';
    lb.classList.add('is-open');
    document.body.style.overflow = 'hidden';
    // Focus the close button so Esc / keyboard works
    var closeBtn = lb.querySelector('.fig-lightbox__close');
    if (closeBtn) closeBtn.focus();
  }

  function closeLightbox() {
    var lb = document.querySelector('.fig-lightbox');
    if (!lb) return;
    lb.classList.remove('is-open');
    document.body.style.overflow = '';
  }

  // If a figure image fails to load (e.g. a cloud-sync placeholder file
  // that hasn't hydrated yet), swap the native broken-image icon + raw
  // alt-text overflow for a calm placeholder so hotspots and layout
  // still look intentional instead of broken.
  function showFigureFallback(img) {
    img.classList.add('figure-block__image--broken');
    var stage = img.closest('.figure-block__stage');
    if (!stage || stage.querySelector('.figure-block__fallback')) return;
    var fallback = document.createElement('div');
    fallback.className = 'figure-block__fallback';
    fallback.innerHTML =
      '<span class="figure-block__fallback-icon" aria-hidden="true">&#128444;&#65039;</span>' +
      '<span class="figure-block__fallback-text">Figure still syncing — check back shortly.</span>';
    stage.appendChild(fallback);
  }

  function bindImages() {
    var imgs = document.querySelectorAll('.figure-block__image');
    Array.prototype.forEach.call(imgs, function (img) {
      if (img.dataset.bound === '1') return;
      img.dataset.bound = '1';
      img.addEventListener('click', function () {
        if (img.classList.contains('figure-block__image--broken')) return;
        var full = img.getAttribute('data-full-src') || img.getAttribute('src');
        openLightbox(full, img.getAttribute('alt') || '');
      });
      img.addEventListener('keydown', function (e) {
        if (e.key === 'Enter' || e.key === ' ') {
          e.preventDefault();
          img.click();
        }
      });
      img.addEventListener('error', function () { showFigureFallback(img); });
      // Image may have already failed before this listener attached
      // (e.g. cached error state on a fast reload).
      if (img.complete && img.naturalWidth === 0) showFigureFallback(img);
      // Make focusable for keyboard activation
      if (!img.getAttribute('tabindex')) img.setAttribute('tabindex', '0');
      img.setAttribute('role', 'button');
      img.setAttribute('aria-label', 'Open larger view: ' + (img.getAttribute('alt') || 'figure'));
    });
  }

  function bindHotspots() {
    var hotspots = document.querySelectorAll('.fig-hotspot');
    Array.prototype.forEach.call(hotspots, function (hs) {
      if (hs.dataset.bound === '1') return;
      hs.dataset.bound = '1';
      var targetSel = hs.getAttribute('data-target');
      if (!targetSel) return;
      hs.setAttribute('role', 'button');
      hs.setAttribute('tabindex', '0');
      hs.addEventListener('click', function (e) {
        e.preventDefault();
        jumpToTarget(targetSel, hs);
      });
      hs.addEventListener('keydown', function (e) {
        if (e.key === 'Enter' || e.key === ' ') {
          e.preventDefault();
          jumpToTarget(targetSel, hs);
        }
      });
    });
  }

  function jumpToTarget(targetSel, hotspot) {
    var target = document.querySelector(targetSel);
    if (!target) {
      console.warn('[figure-viewer] target not found:', targetSel);
      return;
    }
    // Smooth scroll
    var navOffset = 56; // subnav-frosted height
    var y = target.getBoundingClientRect().top + window.pageYOffset - navOffset - 12;
    window.scrollTo({ top: y, behavior: 'smooth' });
    // Pulse animation
    target.classList.remove('fig-pulse-target');
    // Force reflow to restart animation
    void target.offsetWidth;
    target.classList.add('fig-pulse-target');
    setTimeout(function () { target.classList.remove('fig-pulse-target'); }, 3200);
  }

  function init() {
    bindImages();
    bindHotspots();
  }

  window.ARIA = window.ARIA || {};
  window.ARIA.figureViewer = { init: init, openLightbox: openLightbox, closeLightbox: closeLightbox };
})();
