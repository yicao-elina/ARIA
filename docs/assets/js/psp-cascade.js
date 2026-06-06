/**
 * PSPCascade — Animated Processing–Structure–Property hierarchy visualization.
 *
 * Three horizontal bands with nodes and animated connection lines.
 * Uses D3.js v7 and IntersectionObserver for scroll-triggered animation.
 *
 * Exposes global class: PSPCascade
 */
(function () {
  'use strict';

  /* ── colour palette ─────────────────────────────────────────────── */
  const COLORS = {
    jhuBlue:   '#002D72',
    accent:    '#E8600A',
    processing: { bg: '#E8F4FD', border: '#1B6CA8', text: '#002D72' },
    structure:  { bg: '#FFF8E1', border: '#D4930D', text: '#7A5600' },
    property:   { bg: '#E8F5E9', border: '#2E7D32', text: '#1B5E20' },
    shortcut:   '#D32F2F',
    chainLink:  '#002D72',
    highlight:  '#E8600A',
  };

  /* ── PSP data derived from the demo KG ──────────────────────────── */
  const NODES = {
    processing: [
      { id: 'p1', label: 'CVD Temperature\n750°C',    short: 'CVD Temp' },
      { id: 'p2', label: 'Re Doping\n0.1 at%',              short: 'Re Doping' },
      { id: 'p3', label: 'Nb Substitutional\nDoping',        short: 'Nb Doping' },
      { id: 'p4', label: 'Sulfur-Rich\nAtmosphere',          short: 'S-Rich Atm' },
      { id: 'p5', label: 'Annealing\n300°C',           short: 'Anneal' },
      { id: 'p6', label: 'H-Plasma\nTreatment',             short: 'H-Plasma' },
    ],
    structure: [
      { id: 's1', label: 'Crystallinity',         short: 'Crystallinity' },
      { id: 's2', label: 'S-Vacancy\nFormation E', short: 'S-Vac FE' },
      { id: 's3', label: 'Grain Size',             short: 'Grain Size' },
      { id: 's4', label: 'Carrier\nConcentration', short: 'Carrier Conc' },
      { id: 's5', label: 'S/Mo\nStoichiometry',    short: 'S/Mo Ratio' },
      { id: 's6', label: 'Defect\nDensity',        short: 'Defect Den' },
      { id: 's7', label: 'Contact\nResistance',    short: 'Contact Res' },
    ],
    property: [
      { id: 'x1', label: 'Carrier\nMobility',   short: 'Mobility' },
      { id: 'x2', label: 'Drain\nCurrent',       short: 'Drain I' },
      { id: 'x3', label: 'On/Off\nRatio',        short: 'On/Off' },
      { id: 'x4', label: 'n-type\nConductivity', short: 'n-type' },
      { id: 'x5', label: 'Thermal\nConductivity',short: 'κ thermal' },
      { id: 'x6', label: 'Trap State\nDensity',  short: 'Trap States' },
    ],
  };

  /* Complete P→S→P chains (solid arcs) */
  const CHAINS = [
    { path: ['p1', 's1', 'x1'], label: 'CVD Temp → Crystallinity → Mobility' },
    { path: ['p2', 's2', 'x2'], label: 'Re Doping → S-Vac FE → Drain Current' },
    { path: ['p1', 's3', 'x3'], label: 'CVD Temp → Grain Size → On/Off Ratio' },
    { path: ['p3', 's4', 'x4'], label: 'Nb Doping → Carrier Conc → n-type' },
    { path: ['p5', 's6', 'x5'], label: 'Annealing → Defect Density → κ thermal' },
    { path: ['p4', 's5', 'x6'], label: 'S-Rich → S/Mo → Trap States' },
    { path: ['p6', 's7'],        label: 'H-Plasma → Contact Res' },
  ];

  /* Shortcut P→P connections (contextual tunneling) */
  const SHORTCUTS = [
    { path: ['p1', 'x1'], label: 'CVD Temp ⇢ Mobility' },
    { path: ['p2', 'x1'], label: 'Re Doping ⇢ Mobility' },
    { path: ['p3', 'x4'], label: 'Nb Doping ⇢ n-type' },
  ];

  /* ── helper ──────────────────────────────────────────────────────── */
  function lineBreak(selection) {
    return selection.each(function (d) {
      var el = d3.select(this);
      var lines = d.label.split('\n');
      el.text(null);
      lines.forEach(function (line, i) {
        el.append('tspan')
          .attr('x', 0)
          .attr('dy', i === 0 ? '0.35em' : '1.1em')
          .text(line);
      });
    });
  }

  /* ── PSPCascade class ───────────────────────────────────────────── */
  class PSPCascade {
    /**
     * @param {string|d3.Selection} selector  Container element or selector
     * @param {Object} [opts]                 Options
     * @param {number} [opts.width=900]       SVG width
     * @param {number} [opts.height=520]       SVG height
     */
    constructor(selector, opts = {}) {
      this.container = d3.select(selector);
      this.width  = opts.width  || 900;
      this.height = opts.height || 520;
      this.animated = false;
      this.activeChain = null;
      this._build();
    }

    /* ── layout constants ──────────────────────────────────────────── */
    get band() {
      return {
        p: { y: 50,  h: 110, color: COLORS.processing },
        s: { y: 210, h: 110, color: COLORS.structure },
        x: { y: 370, h: 110, color: COLORS.property },
      };
    }

    /* ── build SVG skeleton ───────────────────────────────────────── */
    _build() {
      const W = this.width, H = this.height;

      this.svg = this.container
        .append('svg')
        .attr('viewBox', `0 0 ${W} ${H}`)
        .attr('preserveAspectRatio', 'xMidYMid meet')
        .style('width', '100%')
        .style('max-width', W + 'px')
        .style('font-family', "'Inter', 'Helvetica Neue', Arial, sans-serif");

      /* Defs: glow filter */
      const defs = this.svg.append('defs');
      const glow = defs.append('filter').attr('id', 'psp-glow');
      glow.append('feGaussianBlur').attr('stdDeviation', '4').attr('result', 'blur');
      glow.append('feMerge').selectAll('feMergeNode')
        .data(['blur', 'SourceGraphic'])
        .join('feMergeNode')
        .attr('in', d => d);

      /* Arrow marker */
      defs.append('marker')
        .attr('id', 'psp-arrow')
        .attr('viewBox', '0 0 10 6')
        .attr('refX', 10).attr('refY', 3)
        .attr('markerWidth', 8).attr('markerHeight', 6)
        .attr('orient', 'auto')
        .append('path')
        .attr('d', 'M0,0 L10,3 L0,6 Z')
        .attr('fill', COLORS.chainLink);

      defs.append('marker')
        .attr('id', 'psp-arrow-shortcut')
        .attr('viewBox', '0 0 10 6')
        .attr('refX', 10).attr('refY', 3)
        .attr('markerWidth', 8).attr('markerHeight', 6)
        .attr('orient', 'auto')
        .append('path')
        .attr('d', 'M0,0 L10,3 L0,6 Z')
        .attr('fill', COLORS.shortcut);

      /* Band backgrounds */
      const band = this.band;
      ['p', 's', 'x'].forEach(k => {
        this.svg.append('rect')
          .attr('x', 0).attr('y', band[k].y)
          .attr('width', W).attr('height', band[k].h)
          .attr('fill', band[k].color.bg)
          .attr('stroke', band[k].color.border)
          .attr('stroke-width', 1)
          .attr('rx', 6);
      });

      /* Band labels */
      const bandLabels = [
        { key: 'p', text: 'PROCESSING' },
        { key: 's', text: 'STRUCTURE' },
        { key: 'x', text: 'PROPERTY' },
      ];
      bandLabels.forEach(b => {
        this.svg.append('text')
          .attr('x', 14).attr('y', band[b.key].y + 18)
          .attr('fill', band[b.key].color.text)
          .attr('font-size', 11)
          .attr('font-weight', 700)
          .attr('letter-spacing', '0.1em')
          .text(b.text);
      });

      /* Groups for edges and nodes (edges drawn first so nodes are on top) */
      this.edgeGroup = this.svg.append('g').attr('class', 'psp-edges');
      this.nodeGroup = this.svg.append('g').attr('class', 'psp-nodes');

      /* Position maps */
      this._layoutNodes();

      /* Draw edges (initially invisible) */
      this._drawEdges();

      /* Draw nodes */
      this._drawNodes();

      /* Legend */
      this._drawLegend();

      /* Badge for contextual tunneling */
      this.badge = this.svg.append('g')
        .attr('class', 'psp-badge')
        .attr('opacity', 0)
        .style('pointer-events', 'none');

      this.badge.append('rect')
        .attr('rx', 4).attr('ry', 4)
        .attr('fill', COLORS.shortcut)
        .attr('width', 210).attr('height', 28);

      this.badge.append('text')
        .attr('x', 105).attr('y', 18)
        .attr('text-anchor', 'middle')
        .attr('fill', '#fff')
        .attr('font-size', 13)
        .attr('font-weight', 700)
        .text('⚠ Contextual Tunneling!');

      /* IntersectionObserver */
      this._observe();
    }

    /* ── compute node centres ──────────────────────────────────────── */
    _layoutNodes() {
      const W = this.width;
      const band = this.band;
      const padX = 80, gapX = 20;

      function layoutRow(arr, cy) {
        const n = arr.length;
        const slotW = (W - 2 * padX) / n;
        arr.forEach((nd, i) => {
          nd.cx = padX + slotW * (i + 0.5);
          nd.cy = cy;
          nd.r = 30;
        });
      }

      layoutRow(NODES.processing, band.p.y + band.p.h / 2 + 8);
      layoutRow(NODES.structure,  band.s.y + band.s.h / 2 + 8);
      layoutRow(NODES.property,  band.x.y + band.x.h / 2 + 8);

      /* Build lookup */
      this.pos = {};
      [...NODES.processing, ...NODES.structure, ...NODES.property].forEach(n => {
        this.pos[n.id] = n;
      });
    }

    /* ── draw edges ────────────────────────────────────────────────── */
    _drawEdges() {
      const pos = this.pos;

      /* Complete chain edges */
      this.chainEdges = [];
      CHAINS.forEach((chain, ci) => {
        for (let i = 0; i < chain.path.length - 1; i++) {
          const src = pos[chain.path[i]];
          const tgt = pos[chain.path[i + 1]];
          const midY = (src.cy + tgt.cy) / 2;
          const pathD = `M${src.cx},${src.cy + src.r} C${src.cx},${midY} ${tgt.cx},${midY} ${tgt.cx},${tgt.cy - tgt.r}`;
          const el = this.edgeGroup.append('path')
            .attr('d', pathD)
            .attr('fill', 'none')
            .attr('stroke', COLORS.chainLink)
            .attr('stroke-width', 2)
            .attr('marker-end', 'url(#psp-arrow)')
            .attr('opacity', 0)
            .attr('stroke-dasharray', function () {
              const len = this.getTotalLength();
              return `${len} ${len}`;
            })
            .attr('stroke-dashoffset', function () { return this.getTotalLength(); })
            .attr('data-chain', ci)
            .attr('data-src', chain.path[i])
            .attr('data-tgt', chain.path[i + 1]);
          this.chainEdges.push(el);
        }
      });

      /* Shortcut edges */
      this.shortcutEdges = [];
      SHORTCUTS.forEach((sc, si) => {
        const src = pos[sc.path[0]];
        const tgt = pos[sc.path[1]];
        const cpx = src.cx + (tgt.cx - src.cx) * 0.3;
        const cpy1 = src.cy + 50;
        const cpy2 = tgt.cy - 50;
        const pathD = `M${src.cx},${src.cy + src.r} C${cpx},${cpy1} ${cpx},${cpy2} ${tgt.cx},${tgt.cy - tgt.r}`;
        const el = this.edgeGroup.append('path')
          .attr('d', pathD)
          .attr('fill', 'none')
          .attr('stroke', COLORS.shortcut)
          .attr('stroke-width', 1.5)
          .attr('stroke-dasharray', '6 3')
          .attr('marker-end', 'url(#psp-arrow-shortcut)')
          .attr('opacity', 0)
          .attr('data-shortcut', si)
          .attr('data-src', sc.path[0])
          .attr('data-tgt', sc.path[1]);
        this.shortcutEdges.push(el);
      });
    }

    /* ── draw nodes ────────────────────────────────────────────────── */
    _drawNodes() {
      const band = this.band;

      const allNodes = [
        ...NODES.processing.map(n => ({ ...n, tier: 'p' })),
        ...NODES.structure.map(n => ({ ...n, tier: 's' })),
        ...NODES.property.map(n => ({ ...n, tier: 'x' })),
      ];

      const groups = this.nodeGroup.selectAll('.psp-node')
        .data(allNodes, d => d.id)
        .join('g')
        .attr('class', 'psp-node')
        .attr('transform', d => `translate(${d.cx},${d.cy})`)
        .style('cursor', 'pointer')
        .attr('opacity', 0);

      /* Circle */
      groups.append('circle')
        .attr('r', d => d.r)
        .attr('fill', d => band[d.tier].color.bg)
        .attr('stroke', d => band[d.tier].color.border)
        .attr('stroke-width', 2);

      /* Label */
      groups.append('text')
        .attr('text-anchor', 'middle')
        .attr('font-size', 10)
        .attr('fill', d => band[d.tier].color.text)
        .attr('font-weight', 600)
        .call(lineBreak);

      /* Interaction */
      groups
        .on('mouseenter', (ev, d) => this._hover(d))
        .on('mouseleave', () => this._unhover())
        .on('click', (ev, d) => this._click(d));

      this.nodeEls = groups;
    }

    /* ── hover logic ──────────────────────────────────────────────── */
    _hover(node) {
      if (this.activeChain !== null) return;
      const id = node.id;

      /* Connected edges */
      const connectedIds = new Set([id]);
      this.chainEdges.forEach(el => {
        const s = el.attr('data-src');
        const t = el.attr('data-tgt');
        if (s === id || t === id) {
          connectedIds.add(s);
          connectedIds.add(t);
          el.attr('stroke', COLORS.highlight).attr('stroke-width', 3);
        }
      });
      this.shortcutEdges.forEach(el => {
        const s = el.attr('data-src');
        const t = el.attr('data-tgt');
        if (s === id || t === id) {
          connectedIds.add(s);
          connectedIds.add(t);
          el.attr('stroke', COLORS.accent).attr('stroke-width', 2.5);
        }
      });

      /* Dim unconnected nodes */
      this.nodeEls.transition().duration(200)
        .attr('opacity', d => connectedIds.has(d.id) ? 1 : 0.25);
    }

    _unhover() {
      if (this.activeChain !== null) return;
      this.chainEdges.forEach(el => {
        el.attr('stroke', COLORS.chainLink).attr('stroke-width', 2);
      });
      this.shortcutEdges.forEach(el => {
        el.attr('stroke', COLORS.shortcut).attr('stroke-width', 1.5);
      });
      this.nodeEls.transition().duration(200).attr('opacity', 1);
    }

    /* ── click logic ──────────────────────────────────────────────── */
    _click(node) {
      /* If something is already active, toggle off */
      if (this.activeChain !== null) {
        this._clearClick();
        return;
      }

      /* Check if node is part of a shortcut */
      for (let i = 0; i < SHORTCUTS.length; i++) {
        if (SHORTCUTS[i].path.includes(node.id)) {
          this._highlightShortcut(i);
          return;
        }
      }

      /* Check if node is part of a chain */
      for (let i = 0; i < CHAINS.length; i++) {
        if (CHAINS[i].path.includes(node.id)) {
          this._highlightChain(i);
          return;
        }
      }
    }

    _highlightChain(ci) {
      this.activeChain = { type: 'chain', idx: ci };
      const chainIds = new Set(CHAINS[ci].path);

      this.chainEdges.forEach(el => {
        const eCI = +el.attr('data-chain');
        if (eCI === ci) {
          el.attr('stroke', COLORS.highlight)
            .attr('stroke-width', 3)
            .attr('filter', 'url(#psp-glow)');
        } else {
          el.attr('opacity', 0.12);
        }
      });
      this.shortcutEdges.forEach(el => el.attr('opacity', 0.12));
      this.nodeEls.transition().duration(250)
        .attr('opacity', d => chainIds.has(d.id) ? 1 : 0.18);
    }

    _highlightShortcut(si) {
      this.activeChain = { type: 'shortcut', idx: si };
      const scIds = new Set(SHORTCUTS[si].path);

      this.shortcutEdges.forEach(el => {
        const eSI = +el.attr('data-shortcut');
        if (eSI === si) {
          el.attr('stroke', COLORS.shortcut)
            .attr('stroke-width', 3)
            .attr('filter', 'url(#psp-glow)');
        } else {
          el.attr('opacity', 0.12);
        }
      });
      this.chainEdges.forEach(el => el.attr('opacity', 0.12));
      this.nodeEls.transition().duration(250)
        .attr('opacity', d => scIds.has(d.id) ? 1 : 0.18);

      /* Show badge */
      const src = this.pos[SHORTCUTS[si].path[0]];
      const tgt = this.pos[SHORTCUTS[si].path[1]];
      const bx = (src.cx + tgt.cx) / 2 - 105;
      const by = Math.max(src.cy, tgt.cy) - 60;
      this.badge
        .attr('transform', `translate(${bx},${by})`)
        .transition().duration(300)
        .attr('opacity', 1);
    }

    _clearClick() {
      this.activeChain = null;
      this.badge.transition().duration(200).attr('opacity', 0);

      this.chainEdges.forEach(el => {
        el.attr('stroke', COLORS.chainLink)
          .attr('stroke-width', 2)
          .attr('opacity', 1)
          .attr('filter', null);
      });
      this.shortcutEdges.forEach(el => {
        el.attr('stroke', COLORS.shortcut)
          .attr('stroke-width', 1.5)
          .attr('opacity', 1)
          .attr('filter', null);
      });
      this.nodeEls.transition().duration(250).attr('opacity', 1);
    }

    /* ── scroll-triggered animation ────────────────────────────────── */
    _observe() {
      const node = this.container.node();
      if (!node) return;
      const observer = new IntersectionObserver(entries => {
        entries.forEach(entry => {
          if (entry.isIntersecting && !this.animated) {
            this.animated = true;
            this._animateIn();
          }
        });
      }, { threshold: 0.25 });
      observer.observe(node);
    }

    _animateIn() {
      /* Fade in nodes staggered */
      this.nodeEls
        .transition()
        .delay((d, i) => i * 60)
        .duration(400)
        .attr('opacity', 1);

      /* Animate chain edges drawing */
      this.chainEdges.forEach((el, i) => {
        const len = el.node().getTotalLength();
        el
          .attr('stroke-dasharray', `${len} ${len}`)
          .attr('stroke-dashoffset', len)
          .transition()
          .delay(300 + i * 150)
          .duration(800)
          .attr('stroke-dashoffset', 0)
          .attr('opacity', 1)
          .on('end', function () {
            d3.select(this).attr('stroke-dasharray', null);
          });
      });

      /* Fade in shortcut edges */
      this.shortcutEdges.forEach((el, i) => {
        el
          .transition()
          .delay(1800 + i * 200)
          .duration(500)
          .attr('opacity', 0.55);
      });
    }

    /* ── legend ────────────────────────────────────────────────────── */
    _drawLegend() {
      const g = this.svg.append('g')
        .attr('transform', `translate(${this.width - 260}, ${this.height - 48})`);

      g.append('line')
        .attr('x1', 0).attr('y1', 0).attr('x2', 28).attr('y2', 0)
        .attr('stroke', COLORS.chainLink).attr('stroke-width', 2)
        .attr('marker-end', 'url(#psp-arrow)');
      g.append('text')
        .attr('x', 34).attr('y', 4)
        .attr('font-size', 11)
        .attr('fill', '#555')
        .text('Complete P→S→P chain');

      g.append('line')
        .attr('x1', 0).attr('y1', 18).attr('x2', 28).attr('y2', 18)
        .attr('stroke', COLORS.shortcut).attr('stroke-width', 1.5)
        .attr('stroke-dasharray', '6 3')
        .attr('marker-end', 'url(#psp-arrow-shortcut)');
      g.append('text')
        .attr('x', 34).attr('y', 22)
        .attr('font-size', 11)
        .attr('fill', '#555')
        .text('P→P shortcut (tunneling)');
    }
  }

  /* ── expose globally ────────────────────────────────────────────── */
  window.PSPCascade = PSPCascade;
})();