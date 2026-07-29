/**
 * ARIA — Main Initialization Script
 * Apple Design System Edition
 *
 * Handles scroll animations, sub-nav highlighting,
 * interactive figure initialization, BibTeX copy, math rendering,
 * mobile menu, and smooth scrolling.
 *
 * No longer depends on Distill template.
 */

(function () {
  'use strict';

  // ---------------------------------------------------------------------------
  // Globals exposed for interactive components
  // ---------------------------------------------------------------------------
  window.ARIA = window.ARIA || {};

  var components = [
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

  function qs(sel, ctx) {
    return (ctx || document).querySelector(sel);
  }

  function qsa(sel, ctx) {
    return Array.from((ctx || document).querySelectorAll(sel));
  }

  function debounce(fn, delay) {
    var timer;
    return function () {
      var args = arguments;
      var self = this;
      clearTimeout(timer);
      timer = setTimeout(function () {
        fn.apply(self, args);
      }, delay);
    };
  }

  async function fetchJSON(url) {
    try {
      var res = await fetch(url);
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
    var observerOptions = {
      threshold: 0.1,
      rootMargin: '0px 0px -40px 0px',
    };

    var fadeObserver = new IntersectionObserver(function (entries) {
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

    // Stagger animation delays for grouped elements
    qsa('[data-stagger]').forEach(function (group) {
      var children = qsa('.fade-in, .slide-up', group);
      children.forEach(function (child, i) {
        child.style.transitionDelay = i * 80 + 'ms';
      });
    });
  }

  // ---------------------------------------------------------------------------
  // 2. Sub-nav section highlighting
  // ---------------------------------------------------------------------------

  function initSubNavHighlighting() {
    var subNavLinks = qsa('.sub-nav__link');
    var sections = qsa('section.tile[id]');
    if (!subNavLinks.length || !sections.length) return;

    var headerOffset = 80; // 52px nav + some margin

    function updateActiveSection() {
      var scrollY = window.scrollY;
      var activeId = '';

      sections.forEach(function (section) {
        var top = section.getBoundingClientRect().top + scrollY - headerOffset;
        if (scrollY >= top) {
          activeId = section.id;
        }
      });

      subNavLinks.forEach(function (link) {
        link.classList.remove('active');
        var href = link.getAttribute('href');
        if (href && href === '#' + activeId) {
          link.classList.add('active');
        }
      });
    }

    window.addEventListener('scroll', debounce(updateActiveSection, 50));
    updateActiveSection();
  }

  // ---------------------------------------------------------------------------
  // 3. Collapsible sections
  // ---------------------------------------------------------------------------

  function initCollapsibles() {
    qsa('.collapsible-header').forEach(function (header) {
      var content = header.nextElementSibling;
      if (!content || !content.classList.contains('collapsible-content')) return;

      if (header.classList.contains('open')) {
        content.style.maxHeight = content.scrollHeight + 'px';
      } else {
        content.style.maxHeight = '0px';
      }

      header.addEventListener('click', function () {
        var isOpen = header.classList.toggle('open');

        var arrow = qs('.collapsible-arrow', header);
        if (arrow) {
          arrow.style.transform = isOpen ? 'rotate(180deg)' : 'rotate(0deg)';
        }

        if (isOpen) {
          content.style.maxHeight = content.scrollHeight + 'px';
          var onEnd = function () {
            if (header.classList.contains('open')) {
              content.style.maxHeight = 'none';
            }
            content.removeEventListener('transitionend', onEnd);
          };
          content.addEventListener('transitionend', onEnd);
        } else {
          content.style.maxHeight = content.scrollHeight + 'px';
          content.offsetHeight; // force reflow
          content.style.maxHeight = '0px';
        }
      });
    });
  }

  // ---------------------------------------------------------------------------
  // 4. Interactive figure initialization (lazy-loaded)
  // ---------------------------------------------------------------------------

  function lazyInit(containerSel, initFn) {
    var container = qs(containerSel);
    if (!container) return;

    var observer = new IntersectionObserver(
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
        rootMargin: '200% 0px',
        threshold: 0,
      }
    );

    observer.observe(container);
  }

  async function initInteractiveFigures() {
    var kgData = await fetchJSON('assets/data/aria_2d_kg_demo.json');
    var queryData = await fetchJSON('assets/data/example_queries.json');

    // KGExplorer — note: ID matches HTML, no "-container" suffix
    lazyInit('#kg-explorer', function (container) {
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
        // KGExplorer builds its DOM lazily via an explicit init() call
        // (constructor only sets up state). Without this the container
        // stays empty even though the class loaded successfully.
        if (window.ARIA.KGExplorer && typeof window.ARIA.KGExplorer.init === 'function') {
          window.ARIA.KGExplorer.init();
        }
      } catch (err) {
        console.error('[ARIA] KGExplorer init failed', err);
      }
    });

    // TierRouter — TierRouter takes a container id string
    lazyInit('#tier-router', function (container) {
      if (!queryData) {
        console.error('[ARIA] Query data not available, skipping TierRouter');
        return;
      }
      try {
        if (typeof window.ARIA._TierRouter === 'function') {
          window.ARIA.TierRouter = new window.ARIA._TierRouter('tier-router', queryData);
        } else if (typeof TierRouter === 'function') {
          window.ARIA.TierRouter = new TierRouter('tier-router', queryData);
        } else {
          console.warn('[ARIA] TierRouter class not found');
        }
      } catch (err) {
        console.error('[ARIA] TierRouter init failed', err);
      }
    });

    // PSPCascade
    lazyInit('#psp-cascade', function (container) {
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

    // TunnelingDemo
    lazyInit('#tunneling-demo', function (container) {
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

    // ResultsChart
    lazyInit('#results-chart', function (container) {
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

    // RobustnessSlider
    lazyInit('#robustness-slider', function (container) {
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
    var copyBtn = qs('#copy-bibtex');
    if (!copyBtn) return;

    copyBtn.addEventListener('click', function (e) {
      e.preventDefault();
      var bibtexEl = qs('#bibtex-content');
      if (!bibtexEl) return;

      var text = bibtexEl.textContent.trim();
      navigator.clipboard
        .writeText(text)
        .then(function () {
          var original = copyBtn.textContent;
          copyBtn.textContent = 'Copied!';
          copyBtn.classList.add('copied');
          setTimeout(function () {
            copyBtn.textContent = original;
            copyBtn.classList.remove('copied');
          }, 2000);
        })
        .catch(function () {
          // Fallback for older browsers
          var textarea = document.createElement('textarea');
          textarea.value = text;
          textarea.style.position = 'fixed';
          textarea.style.opacity = '0';
          document.body.appendChild(textarea);
          textarea.select();
          try {
            document.execCommand('copy');
            var original = copyBtn.textContent;
            copyBtn.textContent = 'Copied!';
            setTimeout(function () {
              copyBtn.textContent = original;
            }, 2000);
          } catch (err) {
            console.error('[ARIA] Clipboard copy failed', err);
          }
          document.body.removeChild(textarea);
        });
    });
  }

  // ---------------------------------------------------------------------------
  // 6. Math rendering (KaTeX)
  // ---------------------------------------------------------------------------

  function initMathRendering() {
    if (typeof katex === 'undefined') return;

    qsa('main, .main-content, .tile__content').forEach(function (container) {
      if (!container) return;

      var html = container.innerHTML;

      // Block math: $$...$$
      var rendered = html.replace(/\$\$([\s\S]*?)\$\$/g, function (match, tex) {
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

      // Inline math: $...$
      var finalHtml = rendered.replace(/\$([^\$]+?)\$/g, function (match, tex) {
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
    var menuBtn = qs('.global-nav__hamburger');
    var subNavLinks = qs('.sub-nav__links');

    if (!menuBtn) return;

    menuBtn.addEventListener('click', function () {
      var expanded = menuBtn.getAttribute('aria-expanded') === 'true';
      menuBtn.setAttribute('aria-expanded', String(!expanded));

      if (subNavLinks) {
        subNavLinks.style.display = subNavLinks.style.display === 'flex' ? 'none' : 'flex';
        subNavLinks.style.flexDirection = 'column';
        subNavLinks.style.position = 'absolute';
        subNavLinks.style.top = '100%';
        subNavLinks.style.left = '0';
        subNavLinks.style.right = '0';
        subNavLinks.style.background = 'var(--apple-parchment)';
        subNavLinks.style.padding = '12px';
        subNavLinks.style.boxShadow = '0 4px 12px rgba(0,0,0,0.1)';
      }
    });
  }

  // ---------------------------------------------------------------------------
  // 8. Smooth scroll with header offset
  // ---------------------------------------------------------------------------

  function initSmoothScroll() {
    document.documentElement.style.scrollBehavior = 'smooth';

    document.addEventListener('click', function (e) {
      var anchor = e.target.closest('a[href^="#"]');
      if (!anchor) return;

      var targetId = anchor.getAttribute('href').slice(1);
      if (!targetId) return;

      var targetEl = document.getElementById(targetId);
      if (!targetEl) return;

      e.preventDefault();

      // Header offset = 52px (sub-nav only)
      var headerOffset = 52;
      var y = targetEl.getBoundingClientRect().top + window.pageYOffset - headerOffset;

      window.scrollTo({ top: y, behavior: 'smooth' });

      // Update URL hash without jumping
      history.pushState(null, '', '#' + targetId);
    });
  }

  // ---------------------------------------------------------------------------
  // 9. Results table toggle
  // ---------------------------------------------------------------------------

  function initResultsToggle() {
    var btn = qs('#results-toggle-btn');
    var container = qs('#results-table-container');
    if (!btn || !container) return;

    btn.addEventListener('click', function () {
      var isOpen = container.classList.toggle('open');
      btn.classList.toggle('open', isOpen);
      btn.setAttribute('aria-expanded', String(isOpen));
    });
  }

  // ---------------------------------------------------------------------------
  // Boot sequence
  // ---------------------------------------------------------------------------


  // Local helper: render only block + inline math in a single root.
  function renderMathIn(root) {
    if (typeof katex === 'undefined' || !root) return;
    var html = root.innerHTML;
    var rendered = html.replace(/\$\$([\s\S]*?)\$\$/g, function (m, tex) {
      try { return '<span class="katex-display">' + katex.renderToString(tex.trim(), {displayMode:true, throwOnError:false}) + '</span>'; }
      catch (e) { return m; }
    });
    var finalHtml = rendered.replace(/\$([^\$]+?)\$/g, function (m, tex) {
      try { return katex.renderToString(tex.trim(), {displayMode:false, throwOnError:false}); }
      catch (e) { return m; }
    });
    if (finalHtml !== html) root.innerHTML = finalHtml;
  }

  async function boot() {
    // ARIA style-lift: trigger hero entrance + mesh tab-pause + reduced-motion / touch detection
    try {
      requestAnimationFrame(function () {
        requestAnimationFrame(function () {
          document.body.classList.add('hero-ready');
        });
      });
      document.addEventListener('visibilitychange', function () {
        document.querySelectorAll('.mesh').forEach(function (m) {
          if (document.hidden) m.classList.add('is-paused');
          else m.classList.remove('is-paused');
        });
      });
      if (window.matchMedia('(prefers-reduced-motion: reduce)').matches) {
        document.body.classList.add('no-motion');
      }
      if (window.matchMedia('(hover: none)').matches) {
        document.body.classList.add('no-spotlight');
      }

      // Mark result/chart surfaces so the glass-card spotlight + float
      // don't compete with the data. The user wants to read the chart,
      // not be distracted by a glowing cursor trail.
      qsa('.interactive-figure, #mt-table-host, #mt-column-charts, #mt-stat-tests, #mt-tier-donut, #main-table-root, #results-chart')
        .forEach(function (el) {
          if (!el) return;
          el.classList.add('glass-card--no-tilt');
          el.classList.add('glass-card--no-spotlight');
          el.classList.add('glass-card--no-float');
        });
    } catch (err) { console.error('[ARIA] style-lift init failed', err); }

    try { initScrollAnimations(); } catch (err) { console.error('[ARIA] Scroll animations init failed', err); }
    try { initSubNavHighlighting(); } catch (err) { console.error('[ARIA] Sub-nav highlighting failed', err); }
    try { initCollapsibles(); } catch (err) { console.error('[ARIA] Collapsibles init failed', err); }
    try { initCopyBibtex(); } catch (err) { console.error('[ARIA] Copy BibTeX init failed', err); }
    try { initMobileMenu(); } catch (err) { console.error('[ARIA] Mobile menu init failed', err); }
    try { initSmoothScroll(); } catch (err) { console.error('[ARIA] Smooth scroll init failed', err); }
    try { initMathRendering(); } catch (err) { console.error('[ARIA] Math rendering init failed', err); }
    try { await initInteractiveFigures(); } catch (err) { console.error('[ARIA] Interactive figures init failed', err); }
    try { initResultsToggle(); } catch (err) { console.error('[ARIA] Results toggle init failed', err); }
    try { if (window.ARIA && window.ARIA.figureViewer) window.ARIA.figureViewer.init(); } catch (err) { console.error('[ARIA] Figure viewer init failed', err); }
    try { if (window.ARIA && window.ARIA.mainTable) window.ARIA.mainTable.init(); } catch (err) { console.error('[ARIA] Main table init failed', err); }
    // Re-render math inside JS-injected sections (main-table, figure hotspots, etc.)
    try {
      ['#mt-table-host','#mt-column-charts','#mt-stat-tests','#mt-tier-donut'].forEach(function (sel) {
        var root = qs(sel);
        if (root && !root.querySelector('.katex')) {
          try { renderMathIn(root); } catch (e) {}
        }
      });
    } catch (err) { /* noop */ }
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', boot);
  } else {
    boot();
  }
})();