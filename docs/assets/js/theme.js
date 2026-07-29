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
        // Apple/Morandi-JHU core colors
        primary:        cs.getPropertyValue('--apple-primary').trim()         || '#002D72',
        primaryFocus:   cs.getPropertyValue('--apple-primary-focus').trim()  || '#1a3d8f',
        primaryOnDark:  cs.getPropertyValue('--apple-primary-on-dark').trim()|| '#68ACE5',
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

        // Tier colors (Morandi-JHU)
        tier1:   cs.getPropertyValue('--tier-1').trim()   || '#002D72',
        tier1Bg: cs.getPropertyValue('--tier-1-bg').trim()|| 'rgba(0, 45, 114, 0.06)',
        tier2:   cs.getPropertyValue('--tier-2').trim()   || '#A99400',
        tier2Bg: cs.getPropertyValue('--tier-2-bg').trim()|| 'rgba(169, 148, 0, 0.08)',
        tier3:   cs.getPropertyValue('--tier-3').trim()   || '#6c7a92',
        tier3Bg: cs.getPropertyValue('--tier-3-bg').trim()|| 'rgba(108, 122, 146, 0.06)',

        // Semantic colors (Morandi-JHU)
        success:      cs.getPropertyValue('--aria-success').trim()      || '#2a8a6e',
        successBg:    cs.getPropertyValue('--aria-success-bg').trim()  || 'rgba(42, 138, 110, 0.08)',
        warning:      cs.getPropertyValue('--aria-warning').trim()     || '#A99400',
        warningBg:    cs.getPropertyValue('--aria-warning-bg').trim()  || 'rgba(169, 148, 0, 0.10)',
        danger:       cs.getPropertyValue('--aria-danger').trim()      || '#b8504a',
        dangerBg:     cs.getPropertyValue('--aria-danger-bg').trim()  || 'rgba(184, 80, 74, 0.08)',

        // Light context aliases (everything is light)
        text:       cs.getPropertyValue('--apple-ink').trim()             || '#1d1d1f',
        textMuted:  cs.getPropertyValue('--apple-ink-muted-80').trim()  || '#333333',
        bg:         cs.getPropertyValue('--apple-parchment').trim()       || '#f5f5f7',
        cardBg:     cs.getPropertyValue('--apple-canvas').trim()         || '#ffffff',
        gridLine:   cs.getPropertyValue('--apple-hairline').trim()      || '#e0e0e0',
        border:     cs.getPropertyValue('--apple-divider-soft').trim()  || '#f0f0f0',
        accent:     cs.getPropertyValue('--apple-primary').trim()       || '#002D72',
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