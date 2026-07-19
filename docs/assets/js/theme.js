/**
 * ARIA — Apple Design Theme Module
 *
 * Reads CSS custom properties from design-tokens.css and provides
 * color/theme data to all D3 visualizations.
 *
 * All sections use white/parchment backgrounds — no dark tile context.
 * Every visualization uses the light palette.
 *
 * Must be loaded BEFORE visualization scripts.
 */
(function () {
  'use strict';

  var root = document.documentElement;

  /**
   * Read a CSS custom property value from :root.
   * @param {string} name — e.g. '--apple-primary'
   * @returns {string}
   */
  function readVar(name) {
    return getComputedStyle(root).getPropertyValue(name).trim();
  }

  window.ARIA = window.ARIA || {};

  window.ARIA.theme = {
    /**
     * Get a complete color palette for visualizations.
     * Since all sections are now white/parchment, there's only
     * one context — the light palette.
     *
     * @param {Element} [contextEl] — kept for API compatibility, ignored
     * @returns {Object} color palette
     */
    getColors: function (contextEl) {
      var cs = getComputedStyle(root);

      return {
        // Apple core colors
        primary:        cs.getPropertyValue('--apple-primary').trim()         || '#0066cc',
        primaryFocus:   cs.getPropertyValue('--apple-primary-focus').trim()  || '#0071e3',
        primaryOnDark:  cs.getPropertyValue('--apple-primary-on-dark').trim()|| '#2997ff',
        ink:            cs.getPropertyValue('--apple-ink').trim()             || '#1d1d1f',
        inkMuted80:     cs.getPropertyValue('--apple-ink-muted-80').trim()  || '#333333',
        inkMuted48:     cs.getPropertyValue('--apple-ink-muted-48').trim()  || '#7a7a7a',
        canvas:         cs.getPropertyValue('--apple-canvas').trim()         || '#ffffff',
        parchment:      cs.getPropertyValue('--apple-parchment').trim()      || '#f5f5f7',
        surfacePearl:   cs.getPropertyValue('--apple-surface-pearl').trim() || '#fafafc',
        surfaceTile1:   cs.getPropertyValue('--apple-surface-tile-1').trim()|| '#272729',
        surfaceTile2:   cs.getPropertyValue('--apple-surface-tile-2').trim()|| '#2a2a2c',
        surfaceTile3:   cs.getPropertyValue('--apple-surface-tile-3').trim()|| '#252527',
        hairline:       cs.getPropertyValue('--apple-hairline').trim()      || '#e0e0e0',
        dividerSoft:    cs.getPropertyValue('--apple-divider-soft').trim()  || '#f0f0f0',

        // Tier colors
        tier1:   cs.getPropertyValue('--tier-1').trim()   || '#0066cc',
        tier1Bg: cs.getPropertyValue('--tier-1-bg').trim()|| 'rgba(0, 102, 204, 0.08)',
        tier2:   cs.getPropertyValue('--tier-2').trim()   || '#c9930a',
        tier2Bg: cs.getPropertyValue('--tier-2-bg').trim()|| 'rgba(201, 147, 10, 0.10)',
        tier3:   cs.getPropertyValue('--tier-3').trim()   || '#86868b',
        tier3Bg: cs.getPropertyValue('--tier-3-bg').trim()|| 'rgba(134, 134, 139, 0.08)',

        // Semantic colors
        success:      cs.getPropertyValue('--aria-success').trim()      || '#34c759',
        successBg:    cs.getPropertyValue('--aria-success-bg').trim()  || 'rgba(52, 199, 89, 0.08)',
        warning:      cs.getPropertyValue('--aria-warning').trim()     || '#ff9f0a',
        warningBg:    cs.getPropertyValue('--aria-warning-bg').trim()  || 'rgba(255, 159, 10, 0.10)',
        danger:       cs.getPropertyValue('--aria-danger').trim()      || '#ff3b30',
        dangerBg:     cs.getPropertyValue('--aria-danger-bg').trim()  || 'rgba(255, 59, 48, 0.08)',

        // Light context aliases (everything is light)
        text:       cs.getPropertyValue('--apple-ink').trim()             || '#1d1d1f',
        textMuted:  cs.getPropertyValue('--apple-ink-muted-80').trim()  || '#333333',
        bg:         cs.getPropertyValue('--apple-parchment').trim()       || '#f5f5f7',
        cardBg:     cs.getPropertyValue('--apple-canvas').trim()         || '#ffffff',
        gridLine:   cs.getPropertyValue('--apple-hairline').trim()      || '#e0e0e0',
        border:     cs.getPropertyValue('--apple-divider-soft').trim()  || '#f0f0f0',
        accent:     cs.getPropertyValue('--apple-primary').trim()       || '#0066cc',
      };
    },

    /** Font stack for SVG text elements */
    fontStack: '"SF Pro Text", "Inter", system-ui, -apple-system, BlinkMacSystemFont, sans-serif',

    /** Letter-spacing adjustment for Inter */
    letterSpacing: '-0.01em',

    /** Font feature settings for Inter (rounded "a") */
    fontFeatureSettings: '"ss03"',
  };
})();