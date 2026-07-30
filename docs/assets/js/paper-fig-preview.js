/**
 * ARIA — Paper Figure Preview Modal
 *
 * `.paper-fig-link` anchors (e.g. "Fig 3 See the paper's full KG
 * construction pipeline →") used to be plain <a href="#fig-paper-N">
 * links, so clicking one triggered a native jump straight to the
 * bottom "Paper Figures" section — a long, disorienting scroll.
 *
 * Instead: intercept the click, build a small preview card (thumbnail +
 * caption) from the target <figure> that's already in the DOM, and only
 * scroll to the full figure if the user explicitly asks to via the
 * "View full figure" button.
 *
 * Exposes: window.ARIA.paperFigPreview.init()
 */
;(function () {
  'use strict';

  function getFigureViewer() {
    return (window.ARIA && window.ARIA.figureViewer) || null;
  }

  function buildModal() {
    var modal = document.createElement('div');
    modal.className = 'fig-preview-modal';
    modal.setAttribute('role', 'dialog');
    modal.setAttribute('aria-modal', 'true');
    modal.innerHTML =
      '<div class="fig-preview-modal__card">' +
        '<button class="fig-preview-modal__close" type="button" aria-label="Close">×</button>' +
        '<img class="fig-preview-modal__image" alt="" />' +
        '<div class="fig-preview-modal__caption"></div>' +
        '<button class="fig-preview-modal__cta toggle-btn" type="button">View full figure ↓</button>' +
      '</div>';
    document.body.appendChild(modal);

    modal.addEventListener('click', function (e) {
      if (e.target === modal) closePreview();
    });
    modal.querySelector('.fig-preview-modal__close').addEventListener('click', closePreview);
    modal.querySelector('.fig-preview-modal__image').addEventListener('click', function () {
      var img = modal.querySelector('.fig-preview-modal__image');
      var fv = getFigureViewer();
      if (fv) fv.openLightbox(img.getAttribute('data-full-src') || img.src, img.alt);
    });
    document.addEventListener('keydown', function (e) {
      if (e.key === 'Escape' && modal.classList.contains('is-open')) closePreview();
    });

    return modal;
  }

  function getModal() {
    var modal = document.querySelector('.fig-preview-modal');
    return modal || buildModal();
  }

  function closePreview() {
    var modal = document.querySelector('.fig-preview-modal');
    if (!modal) return;
    modal.classList.remove('is-open');
    document.body.style.overflow = '';
  }

  function openPreview(targetSel, linkEl) {
    var target = document.querySelector(targetSel);
    if (!target) {
      // Target figure missing from the DOM — fall back to the native
      // anchor jump rather than showing an empty preview.
      window.location.hash = targetSel;
      return;
    }

    var img = target.querySelector('.figure-block__image');
    var captionEl = target.querySelector('.figure-block__caption');
    var modal = getModal();

    var modalImg = modal.querySelector('.fig-preview-modal__image');
    modalImg.src = img ? (img.getAttribute('src') || '') : '';
    modalImg.setAttribute('data-full-src', img ? (img.getAttribute('data-full-src') || img.getAttribute('src') || '') : '');
    modalImg.alt = img ? (img.getAttribute('alt') || '') : '';

    var captionHost = modal.querySelector('.fig-preview-modal__caption');
    captionHost.innerHTML = captionEl ? captionEl.innerHTML : '';
    // The cited caption may include a "View PDF" / "Jump to..." link that
    // duplicates the CTA button below — drop it from the preview copy.
    var extraLinks = captionHost.querySelectorAll('a');
    Array.prototype.forEach.call(extraLinks, function (a) { a.remove(); });

    var cta = modal.querySelector('.fig-preview-modal__cta');
    cta.onclick = function () {
      closePreview();
      var fv = getFigureViewer();
      if (fv) {
        fv.jumpToTarget(targetSel, linkEl);
      } else {
        target.scrollIntoView({ behavior: 'smooth', block: 'start' });
      }
    };

    modal.classList.add('is-open');
    document.body.style.overflow = 'hidden';
    modal.querySelector('.fig-preview-modal__close').focus();
  }

  function bindLinks() {
    var links = document.querySelectorAll('.paper-fig-link');
    Array.prototype.forEach.call(links, function (link) {
      if (link.dataset.bound === '1') return;
      link.dataset.bound = '1';
      var a = link.tagName === 'A' ? link : link.querySelector('a');
      if (!a) return;
      var targetSel = a.getAttribute('href');
      if (!targetSel || targetSel.charAt(0) !== '#') return;
      a.addEventListener('click', function (e) {
        e.preventDefault();
        // main.js also has a document-level click listener that
        // smooth-scrolls any a[href^="#"] regardless of preventDefault();
        // stop the event here so it never reaches that handler.
        e.stopPropagation();
        openPreview(targetSel, a);
      });
    });
  }

  function init() {
    bindLinks();
  }

  window.ARIA = window.ARIA || {};
  window.ARIA.paperFigPreview = { init: init, openPreview: openPreview, closePreview: closePreview };

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
})();
