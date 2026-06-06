/**
 * RobustnessSlider — Interactive edge-deletion robustness visualization.
 *
 * Loads data from '../data/benchmark_results.json' (robustness section),
 * falls back to built-in defaults.
 *
 * Exposes global class: RobustnessSlider
 */
(function () {
  'use strict';

  /* ── colour palette ─────────────────────────────────────────────── */
  const COLORS = {
    jhuBlue:   '#002D72',
    accent:    '#E8600A',
    ariaFull:  '#002D72',
    ariaCore:  '#5B9BD5',
    baseline:  '#9E9E9E',
    naiveKG:   '#E53935',
    gridLine:  '#E0E0E0',
    text:      '#333333',
    labelGrey: '#666666',
    trackBg:   '#E0E0E0',
    sliderBg:  '#002D72',
  };

  /* ── default robustness data ──────────────────────────────────────── */
  const DEFAULT_ROBUSTNESS = {
    deletion_levels: [0, 10, 20, 30, 40, 50, 60, 70, 80, 90],
    methods: {
      'ARIA-FULL': [0.82, 0.80, 0.78, 0.75, 0.72, 0.68, 0.64, 0.58, 0.50, 0.38],
      'ARIA-CORE': [0.72, 0.69, 0.66, 0.62, 0.57, 0.51, 0.45, 0.38, 0.30, 0.22],
      'Baseline':   [0.44, 0.43, 0.42, 0.41, 0.39, 0.37, 0.35, 0.33, 0.30, 0.26],
      'Naive KG':   [0.50, 0.47, 0.43, 0.39, 0.34, 0.30, 0.26, 0.22, 0.18, 0.14],
    },
  };

  const METHOD_STYLES = {
    'ARIA-FULL': { color: COLORS.ariaFull,  width: 3.5, dash: null,       label: 'ARIA-FULL' },
    'ARIA-CORE': { color: COLORS.ariaCore,  width: 2.5, dash: null,       label: 'ARIA-CORE' },
    'Baseline':  { color: COLORS.baseline,  width: 2,   dash: '6 3',      label: 'Baseline' },
    'Naive KG':  { color: COLORS.naiveKG,   width: 2,   dash: null,       label: 'Naive KG' },
  };

  /* ── explanatory text at different deletion levels ────────────────── */
  const EXPLANATIONS = [
    { range: [0, 20],  text: 'All methods retain most of their edges. ARIA-FULL and ARIA-CORE show their full causal advantage; Baseline is flat; Naive KG is already losing ground due to uncritical edge injection.' },
    { range: [20, 50], text: 'As edges are deleted, ARIA methods degrade gracefully. The three-tier cascade shifts queries from Tier 1 (direct) to Tier 2 (analogical) and Tier 3 (fallback), absorbing the loss. Naive KG degrades faster because it has no mechanism to assess edge sufficiency.' },
    { range: [50, 70], text: 'ARIA-FULL still benefits from literature search and chain-of-thought reasoning, even as the KG becomes sparse. ARIA-CORE falls back to Tier 3 (pure LLM) for most queries, approaching Baseline performance.' },
    { range: [70, 90], text: 'At ~80% deletion, ARIA-FULL still outperforms all others. The analogical transfer mechanism (Tier 2) absorbs Tier 1 loss by mapping queries to structurally similar pathways — a key resilience property of the three-tier cascade.' },
  ];

  function getExplanation(pct) {
    for (const e of EXPLANATIONS) {
      if (pct >= e.range[0] && pct <= e.range[1]) return e.text;
    }
    return EXPLANATIONS[EXPLANATIONS.length - 1].text;
  }

  /* ── interpolate robustness data ─────────────────────────────────── */
  function interpolateValue(deletionLevels, scores, pct) {
    /* Find surrounding points and linearly interpolate */
    if (pct <= deletionLevels[0]) return scores[0];
    if (pct >= deletionLevels[deletionLevels.length - 1]) return scores[scores.length - 1];
    for (let i = 0; i < deletionLevels.length - 1; i++) {
      if (pct >= deletionLevels[i] && pct <= deletionLevels[i + 1]) {
        const t = (pct - deletionLevels[i]) / (deletionLevels[i + 1] - deletionLevels[i]);
        return scores[i] + t * (scores[i + 1] - scores[i]);
      }
    }
    return scores[0];
  }

  /* ═══════════════════════════════════════════════════════════════════
     RobustnessSlider class
     ═══════════════════════════════════════════════════════════════════ */
  class RobustnessSlider {
    /**
     * @param {string|d3.Selection} selector  Container element or selector
     * @param {Object} [opts]
     * @param {string} [opts.dataPath]  Path to benchmark JSON
     * @param {number} [opts.initialDeletion]  Starting slider position (0-90)
     */
    constructor(selector, opts = {}) {
      this.container = d3.select(selector);
      this.dataPath = opts.dataPath || '../data/benchmark_results.json';
      this.currentDeletion = opts.initialDeletion || 0;
      this.data = null;
      this._loadData().then(() => this._build());
    }

    async _loadData() {
      try {
        const response = await fetch(this.dataPath);
        if (!response.ok) throw new Error(`HTTP ${response.status}`);
        const json = await response.json();
        this.data = json.robustness || DEFAULT_ROBUSTNESS;
      } catch {
        this.data = DEFAULT_ROBUSTNESS;
      }
    }

    _build() {
      this.container.selectAll('*').remove();

      this.root = this.container.append('div')
        .attr('class', 'robustness-slider-root')
        .style('font-family', "'Inter', 'Helvetica Neue', Arial, sans-serif")
        .style('max-width', '720px')
        .style('margin', '0 auto');

      this._buildChart();
      this._buildSlider();
      this._buildExplanation();
      this._update(this.currentDeletion);
    }

    /* ── chart ───────────────────────────────────────────────────────── */
    _buildChart() {
      const data = this.data;
      const margin = { top: 28, right: 24, bottom: 42, left: 48 };
      const W = 660 - margin.left - margin.right;
      const H = 320 - margin.top - margin.bottom;

      this._chartW = W;
      this._chartH = H;

      this.svg = this.root.append('svg')
        .attr('viewBox', `0 0 ${W + margin.left + margin.right} ${H + margin.top + margin.bottom}`)
        .style('width', '100%')
        .style('max-width', '660px')
        .style('height', 'auto');

      this.g = this.svg.append('g')
        .attr('transform', `translate(${margin.left},${margin.top})`);

      /* Scales */
      this._xScale = d3.scaleLinear()
        .domain([0, 90])
        .range([0, W]);

      this._yScale = d3.scaleLinear()
        .domain([0, 0.6])
        .range([H, 0]);

      const x = this._xScale;
      const y = this._yScale;

      /* Grid */
      y.ticks(6).forEach(t => {
        this.g.append('line')
          .attr('x1', 0).attr('x2', W)
          .attr('y1', y(t)).attr('y2', y(t))
          .attr('stroke', COLORS.gridLine)
          .attr('stroke-dasharray', '3 3')
          .attr('stroke-width', 0.5);
      });

      /* Axes */
      this.g.append('g')
        .attr('class', 'x-axis')
        .attr('transform', `translate(0,${H})`)
        .call(d3.axisBottom(x).ticks(9).tickFormat(d => d + '%'))
        .call(g => g.select('.domain').attr('stroke', COLORS.gridLine))
        .call(g => g.selectAll('text').attr('fill', COLORS.labelGrey).attr('font-size', 11));

      this.g.append('g')
        .attr('class', 'y-axis')
        .call(d3.axisLeft(y).ticks(6).tickFormat(d3.format('.1f')))
        .call(g => g.select('.domain').remove())
        .call(g => g.selectAll('text').attr('fill', COLORS.labelGrey).attr('font-size', 11));

      /* Axis labels */
      this.g.append('text')
        .attr('x', W / 2).attr('y', H + 36)
        .attr('text-anchor', 'middle')
        .attr('font-size', 12)
        .attr('fill', COLORS.text)
        .text('Edges Deleted (%)');

      this.g.append('text')
        .attr('transform', 'rotate(-90)')
        .attr('x', -H / 2).attr('y', -36)
        .attr('text-anchor', 'middle')
        .attr('font-size', 12)
        .attr('fill', COLORS.text)
        .text('Overall Score');

      /* Line group (drawn before vertical line so it's behind) */
      this._lineGroup = this.g.append('g').attr('class', 'lines');

      /* Draw each method's line */
      const deletionLevels = data.deletion_levels;
      const methodNames = Object.keys(data.methods);

      methodNames.forEach(name => {
        const style = METHOD_STYLES[name] || { color: '#666', width: 2, dash: null };
        const scores = data.methods[name];
        const points = deletionLevels.map((d, i) => [x(d), y(scores[i])]);

        const lineGen = d3.line()
          .x(d => d[0])
          .y(d => d[1])
          .curve(d3.curveMonotoneX);

        const path = this._lineGroup.append('path')
          .attr('d', lineGen(points))
          .attr('fill', 'none')
          .attr('stroke', style.color)
          .attr('stroke-width', style.width)
          .attr('stroke-dasharray', style.dash || null)
          .attr('opacity', 0.85);

        /* Animate line drawing */
        const totalLen = path.node().getTotalLength();
        path
          .attr('stroke-dasharray', style.dash || `${totalLen} ${totalLen}`)
          .attr('stroke-dashoffset', totalLen)
          .transition()
          .duration(1200)
          .attr('stroke-dashoffset', 0)
          .on('end', function () {
            if (!style.dash) d3.select(this).attr('stroke-dasharray', null);
          });
      });

      /* Annotation at 80% deletion */
      const annX = x(80);
      const annY = y(0.50);
      this.g.append('line')
        .attr('x1', annX).attr('x2', annX)
        .attr('y1', H).attr('y2', y(0.58))
        .attr('stroke', COLORS.accent)
        .attr('stroke-width', 1)
        .attr('stroke-dasharray', '4 2')
        .attr('opacity', 0.7);

      this.g.append('text')
        .attr('x', annX)
        .attr('y', y(0.58) - 6)
        .attr('text-anchor', 'middle')
        .attr('font-size', 9)
        .attr('fill', COLORS.accent)
        .attr('font-weight', 600)
        .text('Tier 2 absorbs')
        .attr('opacity', 0)
        .transition().delay(1400).duration(400).attr('opacity', 1);

      this.g.append('text')
        .attr('x', annX)
        .attr('y', y(0.58) + 6)
        .attr('text-anchor', 'middle')
        .attr('font-size', 9)
        .attr('fill', COLORS.accent)
        .attr('font-weight', 600)
        .text('Tier 1 loss up to ~80%')
        .attr('opacity', 0)
        .transition().delay(1500).duration(400).attr('opacity', 1);

      /* Vertical line at current deletion */
      this._vLine = this.g.append('line')
        .attr('class', 'vline')
        .attr('y1', 0).attr('y2', H)
        .attr('stroke', COLORS.accent)
        .attr('stroke-width', 2)
        .attr('stroke-dasharray', '6 3')
        .attr('opacity', 0.8);

      /* Dots at current deletion */
      this._dots = this.g.append('g').attr('class', 'dots');

      /* Tooltip */
      this._tooltipGroup = this.g.append('g').attr('class', 'tooltip-group');

      /* Legend */
      const legend = this.root.append('div')
        .style('display', 'flex')
        .style('gap', '16px')
        .style('flex-wrap', 'wrap')
        .style('margin-top', '8px')
        .style('justify-content', 'center');

      Object.entries(METHOD_STYLES).forEach(([name, style]) => {
        const item = legend.append('div')
          .style('display', 'flex')
          .style('align-items', 'center')
          .style('gap', '5px');

        item.append('svg')
          .attr('width', 28).attr('height', 8)
          .append('line')
          .attr('x1', 0).attr('y1', 4)
          .attr('x2', 28).attr('y2', 4)
          .attr('stroke', style.color)
          .attr('stroke-width', style.width)
          .attr('stroke-dasharray', style.dash || null);

        item.append('span')
          .style('font-size', '11px')
          .style('color', COLORS.labelGrey)
          .style('font-weight', style.width > 3 ? 700 : 400)
          .text(style.label);
      });
    }

    /* ── slider ──────────────────────────────────────────────────────── */
    _buildSlider() {
      const wrapper = this.root.append('div')
        .style('margin', '20px 0 8px 0')
        .style('padding', '0 4px');

      wrapper.append('label')
        .attr('for', 'robustness-slider')
        .style('font-size', '13px')
        .style('font-weight', 600)
        .style('color', COLORS.text)
        .style('display', 'block')
        .style('margin-bottom', '6px')
        .text('Edge Deletion Level:');

      const sliderRow = wrapper.append('div')
        .style('display', 'flex')
        .style('align-items', 'center')
        .style('gap', '12px');

      sliderRow.append('span')
        .style('font-size', '12px')
        .style('color', COLORS.labelGrey)
        .text('0%');

      this._slider = sliderRow.append('input')
        .attr('type', 'range')
        .attr('id', 'robustness-slider')
        .attr('min', 0)
        .attr('max', 90)
        .attr('step', 1)
        .attr('value', this.currentDeletion)
        .style('flex', '1')
        .style('-webkit-appearance', 'none')
        .style('appearance', 'none')
        .style('height', '8px')
        .style('border-radius', '4px')
        .style('background', `linear-gradient(to right, ${COLORS.jhuBlue} 0%, ${COLORS.jhuBlue} ${this.currentDeletion / 0.9}%, ${COLORS.trackBg} ${this.currentDeletion / 0.9}%, ${COLORS.trackBg} 100%)`)
        .style('outline', 'none')
        .style('cursor', 'pointer')
        .style('accent-color', COLORS.jhuBlue);

      /* Custom slider thumb via style injection */
      const thumbStyle = `
        #robustness-slider::-webkit-slider-thumb {
          -webkit-appearance: none;
          appearance: none;
          width: 20px;
          height: 20px;
          border-radius: 50%;
          background: ${COLORS.jhuBlue};
          border: 3px solid #fff;
          box-shadow: 0 1px 4px rgba(0,0,0,0.25);
          cursor: pointer;
        }
        #robustness-slider::-moz-range-thumb {
          width: 20px;
          height: 20px;
          border-radius: 50%;
          background: ${COLORS.jhuBlue};
          border: 3px solid #fff;
          box-shadow: 0 1px 4px rgba(0,0,0,0.25);
          cursor: pointer;
        }
      `;
      const styleEl = document.createElement('style');
      styleEl.textContent = thumbStyle;
      document.head.appendChild(styleEl);

      this._sliderLabel = sliderRow.append('span')
        .style('font-size', '13px')
        .style('font-weight', 700)
        .style('color', COLORS.jhuBlue)
        .style('min-width', '36px')
        .text(this.currentDeletion + '%');

      sliderRow.append('span')
        .style('font-size', '12px')
        .style('color', COLORS.labelGrey)
        .text('90%');

      /* Event handler */
      const self = this;
      this._slider.on('input', function () {
        const val = +this.value;
        self.currentDeletion = val;
        self._sliderLabel.text(val + '%');
        self._slider.style('background',
          `linear-gradient(to right, ${COLORS.jhuBlue} 0%, ${COLORS.jhuBlue} ${val / 0.9}%, ${COLORS.trackBg} ${val / 0.9}%, ${COLORS.trackBg} 100%)`
        );
        self._update(val);
      });
    }

    /* ── explanation text below chart ────────────────────────────────── */
    _buildExplanation() {
      this._explanationEl = this.root.append('div')
        .style('margin-top', '12px')
        .style('padding', '12px 16px')
        .style('background', '#f5f7fa')
        .style('border-left', `4px solid ${COLORS.jhuBlue}`)
        .style('border-radius', '0 6px 6px 0')
        .style('font-size', '13px')
        .style('line-height', '1.6')
        .style('color', COLORS.text);
    }

    /* ── update on slider change ─────────────────────────────────────── */
    _update(pct) {
      const data = this.data;
      const x = this._xScale;
      const y = this._yScale;
      const H = this._chartH;

      /* Move vertical line */
      this._vLine
        .transition().duration(150)
        .attr('x1', x(pct))
        .attr('x2', x(pct));

      /* Update dots */
      const methodNames = Object.keys(data.methods);
      const dotsData = methodNames.map(name => ({
        name,
        value: interpolateValue(data.deletion_levels, data.methods[name], pct),
        style: METHOD_STYLES[name],
      }));

      const dots = this._dots.selectAll('circle')
        .data(dotsData, d => d.name);

      dots.exit().remove();

      dots.enter()
        .append('circle')
        .attr('r', 5)
        .attr('stroke', '#fff')
        .attr('stroke-width', 2)
        .attr('fill', d => d.style.color)
        .attr('cx', x(pct))
        .attr('cy', d => y(d.value))
        .merge(dots)
        .transition()
        .duration(150)
        .attr('cx', x(pct))
        .attr('cy', d => y(d.value));

      /* Update tooltip */
      this._tooltipGroup.selectAll('*').remove();

      const tooltipX = x(pct) + 12;
      const tooltipAnchorX = tooltipX + 100 > this._chartW ? x(pct) - 120 : tooltipX;

      /* Background */
      const lines = dotsData.map(d =>
        `${d.style.label}: ${(d.value * 100).toFixed(1)}%`
      );

      const bgRect = this._tooltipGroup.append('rect')
        .attr('x', tooltipAnchorX - 6)
        .attr('y', 4)
        .attr('width', 140)
        .attr('height', dotsData.length * 18 + 10)
        .attr('rx', 4)
        .attr('fill', '#fff')
        .attr('stroke', COLORS.gridLine)
        .attr('opacity', 0.92);

      dotsData.forEach((d, i) => {
        this._tooltipGroup.append('text')
          .attr('x', tooltipAnchorX)
          .attr('y', 18 + i * 18)
          .attr('font-size', 11)
          .attr('font-weight', d.name === 'ARIA-FULL' ? 700 : 400)
          .attr('fill', d.style.color)
          .text(`${d.style.label}: ${(d.value * 100).toFixed(1)}%`);
      });

      /* Update explanation */
      this._explanationEl
        .style('opacity', 0)
        .transition().duration(300)
        .style('opacity', 1)
        .text(getExplanation(pct));
    }
  }

  window.RobustnessSlider = RobustnessSlider;
})();