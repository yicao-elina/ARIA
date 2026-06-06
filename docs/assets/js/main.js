/**
 * ARIA - Main Initialization Script
 * Distill.pub-style interactive website
 *
 * Handles scroll animations, sticky TOC, collapsible sections,
 * interactive figure initialization, BibTeX copy, math rendering,
 * mobile menu, and smooth scrolling.
 */

(function () {
  'use strict';

  // ---------------------------------------------------------------------------
  // Globals exposed for interactive components
  // ---------------------------------------------------------------------------
  window.ARIA = window.ARIA || {};

  const components = [
    'KGExplorer',
    'TierRouter',
    'PSPCascade',
    'TunnelingDemo',
    'ResultsChart',
    'RobustnessSlider',
  ];

  components.forEach(function (name) {
    if (!window.ARIA[name]) {
      window.ARIA[name] = null;
    }
  });

  // ---------------------------------------------------------------------------
  // Utility helpers
  // ---------------------------------------------------------------------------

  /**
   * Shorthand for querySelector.
   * @param {string} sel - CSS selector
   * @param {Element} [ctx=document] - Context element
   * @returns {Element|null}
   */
  function qs(sel, ctx) {
    return (ctx || document).querySelector(sel);
  }

  /**
   * Shorthand for querySelectorAll (returns real Array).
   * @param {string} sel - CSS selector
   * @param {Element} [ctx=document] - Context element
   * @returns {Element[]}
   */
  function qsa(sel, ctx) {
    return Array.from((ctx || document).querySelectorAll(sel));
  }

  /**
   * Debounce a function by the given delay in milliseconds.
   * @param {Function} fn
   * @param {number} delay
   * @returns {Function}
   */
  function debounce(fn, delay) {
    let timer;
    return function () {
      const args = arguments;
      const self = this;
      clearTimeout(timer);
      timer = setTimeout(function () {
        fn.apply(self, args);
      }, delay);
    };
  }

  /**
   * Safe JSON fetch that returns null on failure.
   * @param {string} url
   * @returns {Promise<Object|null>}
   */
  async function fetchJSON(url) {
    try {
      const res = await fetch(url);
      if (!res.ok) throw new Error('HTTP ' + res.status + ' for ' + url);
      return await res.json();
    } catch (err) {
      console.error('[ARIA] Failed to fetch ' + url, err);
      return null;
    }
  }

  // ---------------------------------------------------------------------------
  // 1. Scroll-triggered animations
  // ---------------------------------------------------------------------------

  function initScrollAnimations() {
    // Default threshold and rootMargin for preloading
    const observerOptions = {
      threshold: 0.1,
      rootMargin: '0px 0px -40px 0px',
    };

    // --- .fade-in elements ---
    const fadeObserver = new IntersectionObserver(function (entries) {
      entries.forEach(function (entry) {
        if (entry.isIntersecting) {
          entry.target.classList.add('visible');
          fadeObserver.unobserve(entry.target);
        }
      });
    }, observerOptions);

    qsa('.fade-in').forEach(function (el) {
      fadeObserver.observe(el);
    });

    // --- .slide-up elements ---
    const slideObserver = new IntersectionObserver(function (entries) {
      entries.forEach(function (entry) {
        if (entry.isIntersecting) {
          entry.target.classList.add('visible');
          slideObserver.unobserve(entry.target);
        }
      });
    }, observerOptions);

    qsa('.slide-up').forEach(function (el) {
      slideObserver.observe(el);
    });

    // --- d-figure sticky / scroll-triggered figures ---
    const figureObserver = new IntersectionObserver(
      function (entries) {
        entries.forEach(function (entry) {
          if (entry.isIntersecting) {
            entry.target.classList.add('onscreen');
            entry.target.classList.remove('offscreen');
            entry.target.dispatchEvent(new CustomEvent('onscreen'));
          } else {
            entry.target.classList.remove('onscreen');
            entry.target.classList.add('offscreen');
            entry.target.dispatchEvent(new CustomEvent('offscreen'));
          }
        });
      },
      { threshold: 0.5 }
    );

    qsa('.d-figure').forEach(function (fig) {
      figureObserver.observe(fig);
    });

    // --- Stagger animation delays for grouped elements ---
    qsa('[data-stagger]').forEach(function (group) {
      const children = qsa('.fade-in, .slide-up', group);
      children.forEach(function (child, i) {
        child.style.transitionDelay = i * 80 + 'ms';
      });
    });
  }

  // ---------------------------------------------------------------------------
  // 2. Sticky Table of Contents
  // ---------------------------------------------------------------------------

  function initTOC() {
    const article = qs('d-article') || qs('article');
    if (!article) return;

    const tocContainer = qs('nav.d-toc') || qs('.d-toc');
    if (!tocContainer) return;

    const headings = qsa('h2, h3', article);
    if (headings.length === 0) return;

    // Build TOC list
    const tocList = document.createElement('ol');
    tocList.classList.add('toc-list');

    let currentH2Item = null;
    let h2Sublist = null;

    headings.forEach(function (heading, idx) {
      // Assign an id if missing
      if (!heading.id) {
        heading.id = 'toc-section-' + idx;
      }

      const li = document.createElement('li');
      const a = document.createElement('a');
      a.href = '#' + heading.id;
      a.textContent = heading.textContent;
      a.classList.add('toc-link');
      li.appendChild(a);

      if (heading.tagName === 'H2') {
        li.classList.add('toc-h2');
        tocList.appendChild(li);
        currentH2Item = li;
        h2Sublist = null;
      } else if (heading.tagName === 'H3') {
        li.classList.add('toc-h3');
        if (currentH2Item && !h2Sublist) {
          h2Sublist = document.createElement('ol');
          h2Sublist.classList.add('toc-sublist');
          currentH2Item.appendChild(h2Sublist);
        }
        if (h2Sublist) {
          h2Sublist.appendChild(li);
        } else {
          tocList.appendChild(li);
        }
      }
    });

    tocContainer.appendChild(tocList);

    // Highlight current section on scroll
    const tocLinks = qsa('.toc-link', tocContainer);

    function updateActiveTOC() {
      const scrollY = window.scrollY;
      const headerOffset = 80;
      let activeIndex = 0;

      headings.forEach(function (heading, i) {
        if (heading.getBoundingClientRect().top + scrollY - headerOffset <= scrollY) {
          activeIndex = i;
        }
      });

      tocLinks.forEach(function (link) {
        link.classList.remove('active');
      });

      if (tocLinks[activeIndex]) {
        tocLinks[activeIndex].classList.add('active');
      }
    }

    window.addEventListener('scroll', debounce(updateActiveTOC, 50));
    updateActiveTOC();

    // Smooth scroll on TOC link click
    tocList.addEventListener('click', function (e) {
      if (e.target.matches('.toc-link')) {
        e.preventDefault();
        const targetId = e.target.getAttribute('href').slice(1);
        const targetEl = document.getElementById(targetId);
        if (targetEl) {
          const yOffset = -80; // sticky header offset
          const y = targetEl.getBoundingClientRect().top + window.pageYOffset + yOffset;
          window.scrollTo({ top: y, behavior: 'smooth' });
        }
        // Close mobile TOC if open
        const mobileToggle = qs('.d-toc-toggle');
        if (mobileToggle && tocContainer.classList.contains('open')) {
          tocContainer.classList.remove('open');
          mobileToggle.classList.remove('open');
        }
      }
    });

    // Mobile collapsible toggle
    const toggleBtn = qs('.d-toc-toggle');
    if (toggleBtn) {
      toggleBtn.addEventListener('click', function () {
        tocContainer.classList.toggle('open');
        toggleBtn.classList.toggle('open');
      });
    }
  }

  // ---------------------------------------------------------------------------
  // 3. Collapsible sections
  // ---------------------------------------------------------------------------

  function initCollapsibles() {
    qsa('.collapsible-header').forEach(function (header) {
      const content = header.nextElementSibling;
      if (!content || !content.classList.contains('collapsible-content')) return;

      // Set initial state
      if (header.classList.contains('open')) {
        content.style.maxHeight = content.scrollHeight + 'px';
      } else {
        content.style.maxHeight = '0px';
      }

      header.addEventListener('click', function () {
        const isOpen = header.classList.toggle('open');

        // Rotate arrow icon
        const arrow = qs('.collapsible-arrow', header);
        if (arrow) {
          arrow.style.transform = isOpen ? 'rotate(180deg)' : 'rotate(0deg)';
        }

        // Animate content height
        if (isOpen) {
          content.style.maxHeight = content.scrollHeight + 'px';
          // After transition, allow dynamic height
          const onEnd = function () {
            if (header.classList.contains('open')) {
              content.style.maxHeight = 'none';
            }
            content.removeEventListener('transitionend', onEnd);
          };
          content.addEventListener('transitionend', onEnd);
        } else {
          // First set to scrollHeight so we can animate from a known value
          content.style.maxHeight = content.scrollHeight + 'px';
          // Force reflow
          content.offsetHeight; // eslint-disable-line no-unused-expressions
          content.style.maxHeight = '0px';
        }
      });
    });
  }

  // ---------------------------------------------------------------------------
  // 4. Interactive figure initialization (lazy-loaded)
  // ---------------------------------------------------------------------------

  /**
   * Create an IntersectionObserver that initializes a component when its
   * container scrolls into view. Uses 2x viewport rootMargin for preloading.
   *
   * @param {string} containerSel - CSS selector for the figure container
   * @param {Function} initFn - Async or sync initialization function
   */
  function lazyInit(containerSel, initFn) {
    const container = qs(containerSel);
    if (!container) return; // Component not present on this page

    const observer = new IntersectionObserver(
      function (entries) {
        entries.forEach(function (entry) {
          if (entry.isIntersecting) {
            observer.unobserve(entry.target);
            try {
              initFn(container);
            } catch (err) {
              console.error('[ARIA] Error initializing ' + containerSel, err);
            }
          }
        });
      },
      {
        // 2x viewport height for preloading before element is visible
        rootMargin: '200% 0px',
        threshold: 0,
      }
    );

    observer.observe(container);
  }

  async function initInteractiveFigures() {
    // --- Load data files in parallel ---
    const [kgData, queryData] = await Promise.all([
      fetchJSON('assets/data/aria_2d_kg_demo.json'),
      fetchJSON('assets/data/example_queries.json'),
    ]);

    // --- KGExplorer ---
    lazyInit('#kg-explorer-container', function (container) {
      if (!kgData) {
        console.error('[ARIA] KG data not available, skipping KGExplorer');
        return;
      }
      try {
        if (typeof window.ARIA._KGExplorer === 'function') {
          window.ARIA.KGExplorer = new window.ARIA._KGExplorer(kgData, container);
        } else if (typeof KGExplorer === 'function') {
          window.ARIA.KGExplorer = new KGExplorer(kgData, container);
        } else {
          console.warn('[ARIA] KGExplorer class not found');
        }
      } catch (err) {
        console.error('[ARIA] KGExplorer init failed', err);
      }
    });

    // --- TierRouter ---
    lazyInit('#tier-router-container', function (container) {
      if (!queryData) {
        console.error('[ARIA] Query data not available, skipping TierRouter');
        return;
      }
      try {
        if (typeof window.ARIA._TierRouter === 'function') {
          window.ARIA.TierRouter = new window.ARIA._TierRouter(queryData, container);
        } else if (typeof TierRouter === 'function') {
          window.ARIA.TierRouter = new TierRouter(queryData, container);
        } else {
          console.warn('[ARIA] TierRouter class not found');
        }
      } catch (err) {
        console.error('[ARIA] TierRouter init failed', err);
      }
    });

    // --- PSPCascade ---
    lazyInit('#psp-cascade-container', function (container) {
      try {
        if (typeof window.ARIA._PSPCascade === 'function') {
          window.ARIA.PSPCascade = new window.ARIA._PSPCascade(container);
        } else if (typeof PSPCascade === 'function') {
          window.ARIA.PSPCascade = new PSPCascade(container);
        } else {
          console.warn('[ARIA] PSPCascade class not found');
        }
      } catch (err) {
        console.error('[ARIA] PSPCascade init failed', err);
      }
    });

    // --- TunnelingDemo ---
    lazyInit('#tunneling-demo-container', function (container) {
      try {
        if (typeof window.ARIA._TunnelingDemo === 'function') {
          window.ARIA.TunnelingDemo = new window.ARIA._TunnelingDemo(container);
        } else if (typeof TunnelingDemo === 'function') {
          window.ARIA.TunnelingDemo = new TunnelingDemo(container);
        } else {
          console.warn('[ARIA] TunnelingDemo class not found');
        }
      } catch (err) {
        console.error('[ARIA] TunnelingDemo init failed', err);
      }
    });

    // --- ResultsChart ---
    lazyInit('#results-chart-container', function (container) {
      try {
        if (typeof window.ARIA._ResultsChart === 'function') {
          window.ARIA.ResultsChart = new window.ARIA._ResultsChart(container);
        } else if (typeof ResultsChart === 'function') {
          window.ARIA.ResultsChart = new ResultsChart(container);
        } else {
          console.warn('[ARIA] ResultsChart class not found');
        }
      } catch (err) {
        console.error('[ARIA] ResultsChart init failed', err);
      }
    });

    // --- RobustnessSlider ---
    lazyInit('#robustness-slider-container', function (container) {
      try {
        if (typeof window.ARIA._RobustnessSlider === 'function') {
          window.ARIA.RobustnessSlider = new window.ARIA._RobustnessSlider(container);
        } else if (typeof RobustnessSlider === 'function') {
          window.ARIA.RobustnessSlider = new RobustnessSlider(container);
        } else {
          console.warn('[ARIA] RobustnessSlider class not found');
        }
      } catch (err) {
        console.error('[ARIA] RobustnessSlider init failed', err);
      }
    });
  }

  // ---------------------------------------------------------------------------
  // 5. Copy BibTeX
  // ---------------------------------------------------------------------------

  function initCopyBibtex() {
    qsa('.copy-bibtex').forEach(function (btn) {
      btn.addEventListener('click', function () {
        // Find the BibTeX content; could be a sibling or nearby element
        const bibtexEl =
          btn.closest('.bibtex-entry') ||
          btn.nextElementSibling ||
          qs('#bibtex-content');

        let text = '';
        if (bibtexEl) {
          if (bibtexEl.tagName === 'TEXTAREA' || bibtexEl.tagName === 'INPUT') {
            text = bibtexEl.value;
          } else {
            text = bibtexEl.textContent.trim();
          }
        } else {
          // Fallback: use data attribute
          text = btn.getAttribute('data-bibtex') || '';
        }

        if (!text) {
          console.warn('[ARIA] No BibTeX content found for copy button');
          return;
        }

        // Copy to clipboard
        navigator.clipboard
          .writeText(text)
          .then(function () {
            showCopyToast(btn);
          })
          .catch(function () {
            // Fallback for older browsers
            const textarea = document.createElement('textarea');
            textarea.value = text;
            textarea.style.position = 'fixed';
            textarea.style.opacity = '0';
            document.body.appendChild(textarea);
            textarea.select();
            try {
              document.execCommand('copy');
              showCopyToast(btn);
            } catch (err) {
              console.error('[ARIA] Clipboard copy failed', err);
            }
            document.body.removeChild(textarea);
          });
      });
    });
  }

  /**
   * Show a brief "Copied!" toast on a button.
   * @param {Element} btn
   */
  function showCopyToast(btn) {
    const original = btn.textContent;
    btn.textContent = 'Copied!';
    btn.classList.add('copied');
    setTimeout(function () {
      btn.textContent = original;
      btn.classList.remove('copied');
    }, 2000);
  }

  // ---------------------------------------------------------------------------
  // 6. Math rendering (KaTeX fallback)
  // ---------------------------------------------------------------------------

  function initMathRendering() {
    // If Distill's built-in math rendering is present, skip
    if (qs('d-math') || qs('script[type="math/tex"]')) return;

    // Check if KaTeX is available
    if (typeof katex === 'undefined') return;

    // Render block-level math ($$...$$)
    qsa('d-article, article, .post-body').forEach(function (container) {
      if (!container) return;

      const html = container.innerHTML;

      // Match $$...$$ blocks (including multiline)
      const rendered = html.replace(/\$\$([\s\S]*?)\$\$/g, function (match, tex) {
        try {
          return (
            '<span class="katex-display">' +
            katex.renderToString(tex.trim(), {
              displayMode: true,
              throwOnError: false,
            }) +
            '</span>'
          );
        } catch (e) {
          console.warn('[ARIA] KaTeX block render error', e);
          return match;
        }
      });

      // Match inline $...$
      const finalHtml = rendered.replace(/\$([^\$]+?)\$/g, function (match, tex) {
        try {
          return katex.renderToString(tex.trim(), {
            displayMode: false,
            throwOnError: false,
          });
        } catch (e) {
          console.warn('[ARIA] KaTeX inline render error', e);
          return match;
        }
      });

      if (finalHtml !== html) {
        container.innerHTML = finalHtml;
      }
    });
  }

  // ---------------------------------------------------------------------------
  // 7. Mobile menu toggle
  // ---------------------------------------------------------------------------

  function initMobileMenu() {
    const menuBtn = qs('.mobile-menu-btn') || qs('.hamburger');
    const mobileNav = qs('.mobile-nav') || qs('.d-toc');

    if (!menuBtn || !mobileNav) return;

    menuBtn.addEventListener('click', function () {
      mobileNav.classList.toggle('open');
      menuBtn.classList.toggle('active');
      // Toggle aria-expanded for accessibility
      const expanded = menuBtn.getAttribute('aria-expanded') === 'true';
      menuBtn.setAttribute('aria-expanded', String(!expanded));
    });

    // Close menu when clicking outside
    document.addEventListener('click', function (e) {
      if (!mobileNav.contains(e.target) && !menuBtn.contains(e.target)) {
        mobileNav.classList.remove('open');
        menuBtn.classList.remove('active');
        menuBtn.setAttribute('aria-expanded', 'false');
      }
    });

    // Close on escape
    document.addEventListener('keydown', function (e) {
      if (e.key === 'Escape' && mobileNav.classList.contains('open')) {
        mobileNav.classList.remove('open');
        menuBtn.classList.remove('active');
        menuBtn.setAttribute('aria-expanded', 'false');
        menuBtn.focus();
      }
    });
  }

  // ---------------------------------------------------------------------------
  // 8. Smooth scroll behavior & header offset
  // ---------------------------------------------------------------------------

  function initSmoothScroll() {
    // Enable smooth scrolling on the html element
    document.documentElement.style.scrollBehavior = 'smooth';

    // Intercept anchor clicks to apply header offset
    document.addEventListener('click', function (e) {
      const anchor = e.target.closest('a[href^="#"]');
      if (!anchor) return;

      const targetId = anchor.getAttribute('href').slice(1);
      if (!targetId) return;

      const targetEl = document.getElementById(targetId);
      if (!targetEl) return;

      e.preventDefault();

      const headerOffset = 80; // matches sticky header height
      const y =
        targetEl.getBoundingClientRect().top + window.pageYOffset - headerOffset;

      window.scrollTo({ top: y, behavior: 'smooth' });

      // Update URL hash without jumping
      history.pushState(null, '', '#' + targetId);
    });
  }

  // ---------------------------------------------------------------------------
  // Boot sequence
  // ---------------------------------------------------------------------------

  async function boot() {
    // 1. Scroll animations (no async dependencies)
    try {
      initScrollAnimations();
    } catch (err) {
      console.error('[ARIA] Scroll animations init failed', err);
    }

    // 2. Sticky TOC
    try {
      initTOC();
    } catch (err) {
      console.error('[ARIA] TOC init failed', err);
    }

    // 3. Collapsible sections
    try {
      initCollapsibles();
    } catch (err) {
      console.error('[ARIA] Collapsibles init failed', err);
    }

    // 4. Interactive figures (async - loads data)
    try {
      await initInteractiveFigures();
    } catch (err) {
      console.error('[ARIA] Interactive figures init failed', err);
    }

    // 5. Copy BibTeX
    try {
      initCopyBibtex();
    } catch (err) {
      console.error('[ARIA] Copy BibTeX init failed', err);
    }

    // 6. Math rendering
    try {
      initMathRendering();
    } catch (err) {
      console.error('[ARIA] Math rendering init failed', err);
    }

    // 7. Mobile menu
    try {
      initMobileMenu();
    } catch (err) {
      console.error('[ARIA] Mobile menu init failed', err);
    }

    // 8. Smooth scroll
    try {
      initSmoothScroll();
    } catch (err) {
      console.error('[ARIA] Smooth scroll init failed', err);
    }
  }

  // ---------------------------------------------------------------------------
  // DOMContentLoaded
  // ---------------------------------------------------------------------------

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', boot);
  } else {
    // DOM already ready (script loaded with defer or at end of body)
    boot();
  }
})();